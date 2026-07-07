#!/usr/bin/env python3
# encoding: utf-8
# Grape Track and Grab - YOLOv8 Ready (当前使用颜色追踪，可轻松切换)

import cv2
import math
import time
import rclpy
import queue
import signal
import threading
import numpy as np
import message_filters
from rclpy.node import Node
from std_srvs.srv import SetBool, Trigger
from interfaces.srv import SetString
from sensor_msgs.msg import Image, CameraInfo
from rclpy.executors import MultiThreadedExecutor
from servo_controller_msgs.msg import ServosPosition
from rclpy.callback_groups import ReentrantCallbackGroup
from kinematics.kinematics_control import set_pose_target
from kinematics_msgs.srv import GetRobotPose, SetRobotPose
from servo_controller.bus_servo_control import set_servo_position
import common

# ====================== YOLOv8 可选加载 ======================
try:
    from ultralytics import YOLO
    class GrapeYOLODetector:
        def __init__(self, model_path):
            self.model = YOLO(model_path)
            self.target_class = 0
            self.min_conf = 0.45
            self.enabled = True
        def detect(self, rgb_image):
            results = self.model(rgb_image, conf=self.min_conf, iou=0.45, verbose=False)
            best = None
            best_conf = 0.0
            for result in results:
                for box in result.boxes:
                    if int(box.cls) == self.target_class and float(box.conf) > best_conf:
                        best_conf = float(box.conf)
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cx = (x1 + x2) // 2
                        cy = (y1 + y2) // 2
                        best = (cx, cy, best_conf, (x1, y1, x2, y2))
            return best
except ImportError:
    class GrapeYOLODetector:
        def __init__(self, model_path=None):
            self.enabled = False
        def detect(self, rgb_image):
            return None

def depth_pixel_to_camera(pixel_coords, depth, intrinsics):
    fx, fy, cx, cy = intrinsics
    px, py = pixel_coords
    x = (px - cx) * depth / fx
    y = (py - cy) * depth / fy
    z = depth
    return np.array([x, y, z])


class TrackAndGrabNode(Node):
    hand2cam_tf_matrix = [
        [0.0, 0.0, 1.0, -0.101],
        [-1.0, 0.0, 0.0, 0.01],
        [0.0, -1.0, 0.0, 0.05],
        [0.0, 0.0, 0.0, 1.0]
    ]

    def __init__(self, name):
        rclpy.init()
        super().__init__(name, allow_undeclared_parameters=True, automatically_declare_parameters_from_overrides=True)
        
        self.moving = False
        self.start = False
        self.running = True
        self.stamp = time.time()
        self.last_pitch_yaw = (0, 0)
        self.last_position = (0, 0, 0)
        
        self.joints_pub = self.create_publisher(ServosPosition, '/servo_controller', 1)
        
        # 当前使用颜色追踪（YOLO 未启用）
        self.use_yolo = False
        self.detector = None
        self.tracker = None  # 颜色追踪器
        
        self.get_current_pose_client = self.create_client(GetRobotPose, '/kinematics/get_current_pose')
        self.set_pose_target_client = self.create_client(SetRobotPose, '/kinematics/set_pose_target')
        
        self.create_service(Trigger, '~/start', self.start_srv_callback)
        self.create_service(Trigger, '~/stop', self.stop_srv_callback)
        self.create_service(SetString, '~/set_color', self.set_color_srv_callback)
        
        self.image_queue = queue.Queue(maxsize=2)
        
        rgb_sub = message_filters.Subscriber(self, Image, '/gemini_camera/rgb/image_raw')
        depth_sub = message_filters.Subscriber(self, Image, '/gemini_camera/depth/image_raw')
        info_sub = message_filters.Subscriber(self, CameraInfo, '/gemini_camera/depth/camera_info')
        
        sync = message_filters.ApproximateTimeSynchronizer([rgb_sub, depth_sub, info_sub], 3, 0.03)
        sync.registerCallback(self.multi_callback)
        
        self.timer = self.create_timer(0.0, self.init_process, callback_group=ReentrantCallbackGroup())

    def init_process(self):
        self.timer.cancel()
        set_servo_position(self.joints_pub, 1, ((1, 500), (2, 720), (3, 100), (4, 120), (5, 500), (10, 200)))
        time.sleep(1)
        threading.Thread(target=self.main, daemon=True).start()
        self.get_logger().info('\033[1;32mGrape Track & Grab Node Started (颜色追踪模式)\033[0m')

    def set_color_srv_callback(self, request, response):
        self.get_logger().info(f"Set target color: {request.data}")
        self.target_color = request.data
        self.tracker = ColorTracker(self.target_color)  # 使用原有颜色追踪器
        response.success = True
        return response

    def start_srv_callback(self, request, response):
        self.start = True
        response.success = True
        return response

    def stop_srv_callback(self, request, response):
        self.start = False
        self.moving = False
        set_servo_position(self.joints_pub, 1, ((1, 500), (2, 720), (3, 100), (4, 120), (5, 500), (10, 200)))
        response.success = True
        return response

    def multi_callback(self, ros_rgb_image, ros_depth_image, depth_camera_info):
        if self.image_queue.full():
            self.image_queue.get()
        self.image_queue.put((ros_rgb_image, ros_depth_image, depth_camera_info))

    def get_endpoint(self):
        try:
            endpoint = self.send_request(self.get_current_pose_client, GetRobotPose.Request()).pose
            self.endpoint = common.xyz_quat_to_mat(
                [endpoint.position.x, endpoint.position.y, endpoint.position.z],
                [endpoint.orientation.w, endpoint.orientation.x, endpoint.orientation.y, endpoint.orientation.z]
            )
            return self.endpoint
        except:
            return None

    def pick(self, position):
        if position[2] < 0.2:
            yaw = 80
        else:
            yaw = 30
        self.get_logger().info(f'Picking at: {position}')
        
        msg = set_pose_target(position, yaw, [-180.0, 180.0], 1.0)
        res = self.send_request(self.set_pose_target_client, msg)
        
        if res and res.pulse:
            servo_data = res.pulse
            set_servo_position(self.joints_pub, 1, ((1, servo_data[0]), ))
            time.sleep(1)
            set_servo_position(self.joints_pub, 1.5, ((1, servo_data[0]),(2, servo_data[1]), (3, servo_data[2]),(4, servo_data[3]), (5, servo_data[4])))
            time.sleep(1.5)
        
        set_servo_position(self.joints_pub, 0.5, ((10, 540),))
        time.sleep(1)
        
        position = position.copy()
        position[2] += 0.03
        msg = set_pose_target(position, yaw, [-180.0, 180.0], 1.0)
        res = self.send_request(self.set_pose_target_client, msg)
        
        if res and res.pulse:
            servo_data = res.pulse
            set_servo_position(self.joints_pub, 1, ((1, servo_data[0]),(2, servo_data[1]), (3, servo_data[2]),(4, servo_data[3]), (5, servo_data[4])))
            time.sleep(1)
        
        set_servo_position(self.joints_pub, 1, ((1, 500), (2, 720), (3, 100), (4, 120), (5, 500), (10, 540)))
        time.sleep(1)
        set_servo_position(self.joints_pub, 1, ((1, 125), (2, 635), (3, 120), (4, 200), (5, 500)))
        time.sleep(1)
        set_servo_position(self.joints_pub, 1.5, ((1, 125), (2, 325), (3, 200), (4, 290), (5, 500)))
        time.sleep(1.5)
        set_servo_position(self.joints_pub, 1, ((1, 125), (2, 325), (3, 200), (4, 290), (5, 500), (10, 200)))
        time.sleep(1.5)
        set_servo_position(self.joints_pub, 1, ((1, 500), (2, 720), (3, 100), (4, 150), (5, 500), (10, 200)))
        time.sleep(2)
        
        self.moving = False
        self.stamp = time.time()

    def send_request(self, client, msg):
        future = client.call_async(msg)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def main(self):
        while self.running:
            try:
                ros_rgb_image, ros_depth_image, depth_camera_info = self.image_queue.get(block=True, timeout=1)
            except queue.Empty:
                continue

            try:
                rgb_image = np.ndarray(shape=(ros_rgb_image.height, ros_rgb_image.width, 3), dtype=np.uint8, buffer=ros_rgb_image.data)
                depth_image = np.ndarray(shape=(ros_depth_image.height, ros_depth_image.width), dtype=np.uint16, buffer=ros_depth_image.data)
                result_image = np.copy(rgb_image)

                if self.start and not self.moving:
                    if self.use_yolo and self.detector:
                        detection = self.detector.detect(rgb_image)
                        # YOLO逻辑待后续开启
                        pass
                    else:
                        # 当前使用原有颜色追踪
                        if self.tracker is None:
                            continue
                        result_image, p_y, center, r = self.tracker.proc(rgb_image, result_image, common.get_yaml_data("/home/ubuntu/software/lab_tool/config/lab_config.yaml"))
                        if p_y is not None:
                            set_servo_position(self.joints_pub, 0.02, ((1, int(p_y[1])), (4, int(p_y[0]))))
                            center_x, center_y = center
                            h, w = depth_image.shape[:2]
                            if abs(self.last_pitch_yaw[0] - p_y[0]) < 3 and abs(self.last_pitch_yaw[1] - p_y[1]) < 3:
                                if time.time() - self.stamp > 2:
                                    self.stamp = time.time()
                                    roi = [int(center_y - 40) - 5, int(center_y - 40) + 5, int(center_x) - 5, int(center_x) + 5]
                                    roi = [max(0, x) for x in roi]
                                    roi_distance = depth_image[roi[0]:roi[1], roi[2]:roi[3]]
                                    valid_pixels = roi_distance[np.logical_and(roi_distance > 0, roi_distance < 10000)]
                                    if valid_pixels.size > 0:
                                        dist = round(float(np.mean(valid_pixels) / 1000.0), 3) + 0.01
                                        K = depth_camera_info.k
                                        self.get_endpoint()
                                        if self.endpoint is not None:
                                            position = depth_pixel_to_camera((center_x, center_y - 40), dist, (K[0], K[4], K[2], K[5]))
                                            position[0] -= 0.01
                                            pose_end = np.matmul(self.hand2cam_tf_matrix, common.xyz_euler_to_mat(position, (0, 0, 0)))
                                            world_pose = np.matmul(self.endpoint, pose_end)
                                            pose_t, _ = common.mat_to_xyz_euler(world_pose)
                                            self.moving = True
                                            threading.Thread(target=self.pick, args=(pose_t.tolist(),)).start()
                            self.last_pitch_yaw = p_y
            except Exception as e:
                self.get_logger().error(f'Error: {str(e)}')

        rclpy.shutdown()


# ====================== 原有 ColorTracker 类 ======================
class ColorTracker:
    def __init__(self, target_color):
        self.target_color = target_color
        self.pid_yaw = common.pid.PID(20.5, 1.0, 1.2)   # 注意：如果报错可改成 from sdk import pid
        self.pid_pitch = common.pid.PID(20.5, 1.0, 1.2)
        self.yaw = 500
        self.pitch = 150

    def proc(self, source_image, result_image, color_ranges):
        h, w = source_image.shape[:2]
        color = color_ranges['lab']['gemini_camera'][self.target_color]
        img = cv2.resize(source_image, (int(w/2), int(h/2)))
        img_blur = cv2.GaussianBlur(img, (3, 3), 3)
        img_lab = cv2.cvtColor(img_blur, cv2.COLOR_RGB2LAB)
        mask = cv2.inRange(img_lab, tuple(color['min']), tuple(color['max']))
        eroded = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        dilated = cv2.dilate(eroded, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        contours = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[-2]
        min_c = None
        for c in contours:
            if math.fabs(cv2.contourArea(c)) < 50:
                continue
            (center_x, center_y), radius = cv2.minEnclosingCircle(c)
            if min_c is None or center_x < min_c[1]:
                min_c = (c, center_x)
        if min_c is not None:
            (center_x, center_y), radius = cv2.minEnclosingCircle(min_c[0])
            center_x = center_x * 2
            center_y = center_y * 2
            center_x_1 = center_x / w
            center_y_1 = center_y / h
            if abs(center_x_1 - 0.5) > 0.02:
                self.pid_yaw.SetPoint = 0.5
                self.pid_yaw.update(center_x_1)
                self.yaw = min(max(self.yaw + self.pid_yaw.output, 0), 1000)
            else:
                self.pid_yaw.clear()
            if abs(center_y_1 - 0.5) > 0.02:
                self.pid_pitch.SetPoint = 0.5
                self.pid_pitch.update(center_y_1)
                self.pitch = min(max(self.pitch + self.pid_pitch.output, 100), 720)
            else:
                self.pid_pitch.clear()
            return (result_image, (self.pitch, self.yaw), (center_x, center_y), radius * 2)
        else:
            return (result_image, None, None, 0)


def main():
    node = TrackAndGrabNode('grape_track_grab')
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    executor.spin()
    node.destroy_node()

if __name__ == "__main__":
    main()
