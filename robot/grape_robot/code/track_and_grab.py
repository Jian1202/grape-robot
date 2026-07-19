#!/usr/bin/env python3
# encoding: utf-8
# @data:2023/12/19
# 机械前超前看识别追踪空中指定颜色物品(the mechanical clamp looks forward to recognize and track a specified color object in the air)
# 通过深度相机识别计算物品的空间位置(recognize and calculate the spatial position of objects using a depth camera)
# 完成抓取并放到指定位置(complete the grasping and place the object at the specified location)
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
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sdk import pid, common, fps
from std_srvs.srv import Trigger
from interfaces.srv import SetString
from sensor_msgs.msg import Image, CameraInfo
from orbbec_camera_msgs.msg import Extrinsics
from rclpy.executors import MultiThreadedExecutor
from servo_controller_msgs.msg import ServosPosition
from rclpy.callback_groups import ReentrantCallbackGroup
from kinematics.kinematics_control import set_pose_target
from kinematics_msgs.srv import GetRobotPose, SetRobotPose
from servo_controller.bus_servo_control import set_servo_position
from ultralytics import YOLO
try:
    from .grape_localization import (
        DetectionBox,
        LocalizationConfig,
        RigidTransform,
        enforce_localization_only,
        intrinsics_from_camera_info,
        localize_detection,
    )
    from .target_stability import (
        ObservationGenerationGuard,
        StabilityConfig,
        StabilityFailure,
        TargetStabilityTracker,
        stability_config_from_values,
    )
except ImportError:
    # 兼容在源码目录直接执行脚本；ROS2 console_script 使用上面的包内导入。
    from grape_localization import (
        DetectionBox,
        LocalizationConfig,
        RigidTransform,
        enforce_localization_only,
        intrinsics_from_camera_info,
        localize_detection,
    )
    from target_stability import (
        ObservationGenerationGuard,
        StabilityConfig,
        StabilityFailure,
        TargetStabilityTracker,
        stability_config_from_values,
    )


def depth_pixel_to_camera(pixel_coords, depth, intrinsics):
    fx, fy, cx, cy = intrinsics
    px, py = pixel_coords
    x = (px - cx) * depth / fx
    y = (py - cy) * depth / fy
    z = depth
    return np.array([x, y, z])

class ColorTracker:
    def __init__(self, target_color):
        self.target_color = target_color
        self.pid_yaw = pid.PID(20.5, 1.0, 1.2)
        self.pid_pitch = pid.PID(20.5, 1.0, 1.2)
        self.yaw = 500
        self.pitch = 150
    
    def proc(self, source_image, result_image, color_ranges):
        h, w = source_image.shape[:2]
        color = color_ranges['lab']['gemini_camera'][self.target_color]

        img = cv2.resize(source_image, (int(w/2), int(h/2)))
        img_blur = cv2.GaussianBlur(img, (3, 3), 3) # 高斯模糊(Gaussian blur)
        img_lab = cv2.cvtColor(img_blur, cv2.COLOR_RGB2LAB) # 转换到 LAB 空间(convert to the LAB space)
        mask = cv2.inRange(img_lab, tuple(color['min']), tuple(color['max'])) # 二值化(binarization)

        # 平滑边缘，去除小块，合并靠近的块(smooth the edges, remove small patches, and merge adjacent patches)
        eroded = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        dilated = cv2.dilate(eroded, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        # cv2.imshow('d', mask)
        # 找出最大轮廓(find out the contour with the maximal area)
        contours = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[-2]
        min_c = None
        for c in contours:
            if math.fabs(cv2.contourArea(c)) < 50:
                continue
            (center_x, center_y), radius = cv2.minEnclosingCircle(c) # 最小外接圆(the minimum circumcircle)
            if min_c is None:
                min_c = (c, center_x)
            elif center_x < min_c[1]:
                if center_x < min_c[1]:
                    min_c = (c, center_x)

        # 如果有符合要求的轮廓(if there are contours that meet the requirements)
        if min_c is not None:
            (center_x, center_y), radius = cv2.minEnclosingCircle(min_c[0]) # 最小外接圆(the minimum circumcircle)

            # 圈出识别的的要追踪的色块(encircle the recognized color block to be tracked)
            circle_color = common.range_rgb[self.target_color] if self.target_color in common.range_rgb else (0x55, 0x55, 0x55)
            cv2.circle(result_image, (int(center_x * 2), int(center_y * 2)), int(radius * 2), circle_color, 2)

            center_x = center_x * 2
            center_x_1 = center_x / w
            if abs(center_x_1 - 0.5) > 0.02:  # 相差范围小于一定值就不用再动了(stop moving if the difference range is less than a certain value)
                self.pid_yaw.SetPoint = 0.5  # 我们的目标是要让色块在画面的中心, 就是整个画面的像素宽度的 1/2 位置(our goal is to position the color block at the center of the frame, which is at the halfway point of the entire pixel width of the frame)
                self.pid_yaw.update(center_x_1)
                self.yaw = min(max(self.yaw + self.pid_yaw.output, 0), 1000)
            else:
                self.pid_yaw.clear() # 如果已经到达中心了就复位一下 pid 控制器(if it has already reached the center, reset the PID controller)

            center_y = center_y * 2
            center_y_1 = center_y / h
            if abs(center_y_1 - 0.5) > 0.02:
                self.pid_pitch.SetPoint = 0.5
                self.pid_pitch.update(center_y_1)
                self.pitch = min(max(self.pitch + self.pid_pitch.output, 100), 720)
            else:
                self.pid_pitch.clear()
            target_size = radius * 2
            target_box = (
                center_x - target_size / 2,
                center_y - target_size / 2,
                center_x + target_size / 2,
                center_y + target_size / 2,
            )
            return (result_image, (self.pitch, self.yaw), (center_x, center_y), target_size, target_box)
        else:
            return (result_image, None, None, 0, None)


class YoloTracker(ColorTracker):
    """Use YOLO detections while keeping the original tracker output format."""

    def __init__(self, model_path, target_class='ripe_grape', confidence=0.4, imgsz=320):
        super().__init__(target_class)
        self.target_class = target_class
        self.confidence = float(confidence)
        self.imgsz = int(imgsz)
        self.model = YOLO(model_path)

        class_names = set(self.model.names.values())
        if self.target_class not in class_names:
            raise ValueError(
                f"target_class={self.target_class!r} is not in model classes: "
                f"{sorted(class_names)}"
            )

    def proc(self, source_image, result_image, color_ranges=None):
        h, w = source_image.shape[:2]

        # ROS image is RGB. Ultralytics numpy/OpenCV input is BGR.
        bgr_image = cv2.cvtColor(source_image, cv2.COLOR_RGB2BGR)
        prediction = self.model.predict(
            source=bgr_image,
            conf=self.confidence,
            imgsz=self.imgsz,
            device=0,
            verbose=False,
        )[0]

        detections = []
        if prediction.boxes is not None:
            for box in prediction.boxes:
                class_id = int(box.cls[0].item())
                class_name = self.model.names[class_id]
                if class_name != self.target_class:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = float(box.conf[0].item())
                center_x = (x1 + x2) / 2.0
                center_y = (y1 + y2) / 2.0
                detections.append(
                    {
                        'box': (x1, y1, x2, y2),
                        'center': (center_x, center_y),
                        'confidence': confidence,
                        'class_name': class_name,
                    }
                )

        if not detections:
            return (result_image, None, None, 0, None)

        # Preserve the original behavior: select the leftmost matching target.
        target = min(detections, key=lambda item: item['center'][0])
        x1, y1, x2, y2 = target['box']
        center_x, center_y = target['center']

        cv2.rectangle(
            result_image,
            (int(x1), int(y1)),
            (int(x2), int(y2)),
            (0, 255, 0),
            2,
        )
        label = f"{target['class_name']} {target['confidence']:.2f}"
        cv2.putText(
            result_image,
            label,
            (int(x1), max(20, int(y1) - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        center_x_1 = center_x / w
        if abs(center_x_1 - 0.5) > 0.02:
            self.pid_yaw.SetPoint = 0.5
            self.pid_yaw.update(center_x_1)
            self.yaw = min(max(self.yaw + self.pid_yaw.output, 0), 1000)
        else:
            self.pid_yaw.clear()

        center_y_1 = center_y / h
        if abs(center_y_1 - 0.5) > 0.02:
            self.pid_pitch.SetPoint = 0.5
            self.pid_pitch.update(center_y_1)
            self.pitch = min(max(self.pitch + self.pid_pitch.output, 100), 720)
        else:
            self.pid_pitch.clear()

        target_size = max(x2 - x1, y2 - y1)
        return (
            result_image,
            (self.pitch, self.yaw),
            (center_x, center_y),
            target_size,
            target['box'],
        )


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
        self.fps = fps.FPS()
        self.moving = False
        self.count = 0
        self.start = False
        self.running = True
        self.last_pitch_yaw = (0, 0)

        self.enable_disp = 1
        signal.signal(signal.SIGINT, self.shutdown)
        self.lab_data = common.get_yaml_data("/home/ubuntu/software/lab_tool/config/lab_config.yaml")
        self.last_position = (0, 0, 0)
        self.stamp = time.time()

        self.target_color = None

        parameter_defaults = {
            'start': True,
            'color': 'green',
            'detector': 'yolo',
            'model_path': '/home/ubuntu/grape-yolo/models/grape_v2_best.pt',
            'target_class': 'ripe_grape',
            'confidence': 0.4,
            'imgsz': 320,
            'enable_arm': False,
            'depth_scale_m_per_unit': 0.001,
            'min_valid_points': 20,
            'min_valid_ratio': 0.15,
            'box_inset_ratio': 0.15,
            'stability_required_frames': 3,
            'stability_max_position_delta_m': 0.03,
            'stability_max_target_age_s': 0.2,
        }
        for parameter_name, default_value in parameter_defaults.items():
            if not self.has_parameter(parameter_name):
                self.declare_parameter(parameter_name, default_value)

        self.detector_type = str(self.get_parameter('detector').value)
        self.model_path = str(self.get_parameter('model_path').value)
        self.target_class = str(self.get_parameter('target_class').value)
        self.confidence = float(self.get_parameter('confidence').value)
        self.imgsz = int(self.get_parameter('imgsz').value)
        self.enable_arm = bool(self.get_parameter('enable_arm').value)
        enforce_localization_only(self.enable_arm)
        self.localization_config = LocalizationConfig(
            depth_scale_m_per_unit=float(self.get_parameter('depth_scale_m_per_unit').value),
            min_valid_points=int(self.get_parameter('min_valid_points').value),
            min_valid_ratio=float(self.get_parameter('min_valid_ratio').value),
            box_inset_ratio=float(self.get_parameter('box_inset_ratio').value),
        )
        self.stability_tracker = TargetStabilityTracker(
            stability_config_from_values(
                self.get_parameter('stability_required_frames').value,
                self.get_parameter('stability_max_position_delta_m').value,
                self.get_parameter('stability_max_target_age_s').value,
            )
        )
        self.target_state_lock = threading.Lock()
        self.observation_guard = ObservationGenerationGuard()
        self.observation_guard.reset(self.ros_now_s())
        self.stability_result = self.stability_tracker.reset()

        # 当前阶段不创建执行器 publisher 或运动学 client，避免检测-only节点获得动作通道。
        self.joints_pub = None
        self.get_current_pose_client = None
        self.set_pose_target_client = None

        self.create_service(Trigger, '~/start', self.start_srv_callback)
        self.create_service(Trigger, '~/stop', self.stop_srv_callback)
        self.create_service(SetString, '~/set_color', self.set_color_srv_callback)
        self.tracker = None

        self.image_queue = queue.Queue(maxsize=2)
        self.endpoint = None
        self.rgb_camera_info = None
        self.depth_camera_info = None
        self.depth_to_color = None

        self.start_stamp = time.time() + 3

        rgb_sub = message_filters.Subscriber(self, Image, '/gemini_camera/rgb/image_raw')
        depth_sub = message_filters.Subscriber(self, Image, '/gemini_camera/depth/image_raw')
        self.create_subscription(
            CameraInfo,
            '/gemini_camera/depth/camera_info',
            self.depth_camera_info_callback,
            1,
        )
        self.create_subscription(
            CameraInfo,
            '/gemini_camera/rgb/camera_info',
            self.rgb_camera_info_callback,
            1,
        )
        extrinsics_qos = QoSProfile(depth=1)
        extrinsics_qos.reliability = ReliabilityPolicy.RELIABLE
        extrinsics_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.create_subscription(
            Extrinsics,
            '/gemini_camera/depth_to_color',
            self.depth_to_color_callback,
            extrinsics_qos,
        )

        # 同步时间戳, 时间允许有误差在0.03s(synchronize timestamps, allowing a time deviation of up to 0.03 seconds)
        # CameraInfo 独立缓存；把低频元数据放入逐帧同步会使新图像等待旧内参消息。
        sync = message_filters.ApproximateTimeSynchronizer([rgb_sub, depth_sub], 3, 0.02)
        sync.registerCallback(self.multi_callback) #执行反馈函数(execute feedback function)
        
        timer_cb_group = ReentrantCallbackGroup()
        self.timer = self.create_timer(0.0, self.init_process, callback_group=timer_cb_group)

    def init_process(self):
        self.timer.cancel()

        if self.get_parameter('start').value:
            if self.detector_type == 'yolo':
                self.target_color = self.target_class
                self.tracker = YoloTracker(
                    model_path=self.model_path,
                    target_class=self.target_class,
                    confidence=self.confidence,
                    imgsz=self.imgsz,
                )
                self.start = True
                self.get_logger().info(
                    f'YOLO ready: class={self.target_class}, '
                    f'conf={self.confidence}, imgsz={self.imgsz}, '
                    f'enable_arm={self.enable_arm}'
                )
            else:
                self.target_color = self.get_parameter('color').value
                msg = SetString.Request()
                msg.data = self.target_color
                self.set_color_srv_callback(msg, SetString.Response())

        threading.Thread(target=self.main, daemon=True).start()
        self.create_service(Trigger, '~/init_finish', self.get_node_state)
        self.get_logger().info('\033[1;32m%s\033[0m' % 'start')

    def rgb_camera_info_callback(self, msg):
        self.rgb_camera_info = msg

    def depth_camera_info_callback(self, msg):
        with self.target_state_lock:
            self.depth_camera_info = msg

    def depth_to_color_callback(self, msg):
        self.depth_to_color = msg

    def get_node_state(self, request, response):
        response.success = True
        return response

    def shutdown(self, signum, frame):
        self.running = False

    def _clear_image_queue_locked(self):
        while True:
            try:
                self.image_queue.get_nowait()
            except queue.Empty:
                return

    def _invalidate_target_state_locked(self):
        self.observation_guard.reset(self.ros_now_s())
        self.stability_result = self.stability_tracker.reset()
        self._clear_image_queue_locked()

    def _update_stability_for_generation(
        self,
        generation,
        observation_timestamp_s,
        *,
        position,
        failure=None,
    ):
        with self.target_state_lock:
            if not self.observation_guard.accepts(
                generation, observation_timestamp_s
            ):
                return False, self.stability_result
            self.stability_result = self.stability_tracker.update(
                observation_timestamp_s=observation_timestamp_s,
                now_s=self.ros_now_s(),
                position=position,
                failure=failure,
            )
            return True, self.stability_result

    def set_color_srv_callback(self, request, response):
        self.get_logger().info('\033[1;32m%s\033[0m' % "set_color")
        with self.target_state_lock:
            self.target_color = request.data
            self.tracker = ColorTracker(self.target_color)
            self.start = True
            self._invalidate_target_state_locked()
        self.get_logger().info('\033[1;32mset color: %s\033[0m' % self.target_color)
        response.success = True
        response.message = "set_color"
        return response

    def start_srv_callback(self, request, response):
        self.get_logger().info('\033[1;32m%s\033[0m' % "start")
        with self.target_state_lock:
            self.start = True
            self._invalidate_target_state_locked()
        response.success = True
        response.message = "start"
        return response

    def stop_srv_callback(self, request, response):
        self.get_logger().info('\033[1;32m%s\033[0m' % "stop")
        with self.target_state_lock:
            self.start = False
            self.moving = False
            self.count = 0
            self.last_pitch_yaw = (0, 0)
            self.last_position = (0, 0, 0)
            self._invalidate_target_state_locked()
        if self.enable_arm:
            set_servo_position(self.joints_pub, 1, ((1, 500), (2, 720), (3, 100), (4, 120), (5, 500), (10, 200)))
        response.success = True
        response.message = "stop"
        return response

    def send_request(self, client, msg):
        future = client.call_async(msg)
        while rclpy.ok():
            if future.done() and future.result():
                return future.result()

    def multi_callback(self, ros_rgb_image, ros_depth_image):
        observation_timestamp_s = self.image_timestamp_s(ros_rgb_image)
        with self.target_state_lock:
            generation = self.observation_guard.generation
            if not self.observation_guard.accepts(
                generation, observation_timestamp_s
            ):
                return
            if self.image_queue.full():
                # 如果队列已满，丢弃最旧的图像(if the queue is full, discard the oldest image)
                self.image_queue.get_nowait()
            depth_camera_info = self.depth_camera_info
            self.image_queue.put_nowait(
                (
                    generation,
                    ros_rgb_image,
                    ros_depth_image,
                    depth_camera_info,
                )
            )

    def localize_target(self, depth_image, depth_camera_info, target_box):
        """调用纯算法定位；缺少元数据时返回可显示的失败文本。"""
        if depth_camera_info is None:
            return None, 'DEPTH_CAMERA_INFO_MISSING'
        if self.rgb_camera_info is None:
            return None, 'RGB_CAMERA_INFO_MISSING'
        if self.depth_to_color is None:
            return None, 'DEPTH_TO_COLOR_MISSING'
        if target_box is None:
            return None, 'DETECTION_BOX_MISSING'

        depth_intrinsics = intrinsics_from_camera_info(
            depth_camera_info.width,
            depth_camera_info.height,
            depth_camera_info.k,
        )
        color_intrinsics = intrinsics_from_camera_info(
            self.rgb_camera_info.width,
            self.rgb_camera_info.height,
            self.rgb_camera_info.k,
        )
        rotation = np.asarray(self.depth_to_color.rotation, dtype=np.float64)
        if rotation.size == 9:
            rotation = rotation.reshape((3, 3))
        extrinsics = RigidTransform(
            rotation,
            np.asarray(self.depth_to_color.translation, dtype=np.float64),
        )
        result = localize_detection(
            depth_image=depth_image,
            depth_intrinsics=depth_intrinsics,
            color_intrinsics=color_intrinsics,
            depth_to_color=extrinsics,
            detection_box=DetectionBox(*target_box),
            config=self.localization_config,
        )
        return result, result.failure.value

    def draw_localization_result(
        self, image, result, failure_text, stability_result
    ):
        if result is not None and result.success:
            pixel_x, pixel_y = result.projected_color_pixel
            cv2.circle(
                image,
                (int(round(pixel_x)), int(round(pixel_y))),
                6,
                (255, 255, 255),
                -1,
            )
            text = (
                f'RGBD z={result.depth_median_m:.3f}m '
                f'coverage={result.valid_ratio:.2f} n={result.valid_points}'
            )
            color = (0, 255, 0)
        else:
            text = f'RGBD BLOCKED: {failure_text}'
            color = (255, 80, 80)
        cv2.putText(
            image,
            text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )
        if stability_result.stable:
            stability_text = 'TARGET STABLE'
            stability_color = (0, 255, 0)
        elif stability_result.failure == StabilityFailure.WARMING_UP:
            stability_text = (
                f'TARGET WARMING {stability_result.consecutive_successes}/'
                f'{self.stability_tracker.config.required_frames}'
            )
            stability_color = (255, 220, 0)
        else:
            stability_text = f'TARGET INVALID: {stability_result.failure.value}'
            stability_color = (255, 80, 80)
        cv2.putText(
            image,
            stability_text,
            (10, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            stability_color,
            2,
            cv2.LINE_AA,
        )

    @staticmethod
    def image_timestamp_s(image_msg):
        return float(image_msg.header.stamp.sec) + float(
            image_msg.header.stamp.nanosec
        ) * 1e-9

    def ros_now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def get_endpoint(self):
        endpoint = self.send_request(self.get_current_pose_client, GetRobotPose.Request()).pose
        self.endpoint = common.xyz_quat_to_mat([endpoint.position.x, endpoint.position.y, endpoint.position.z],
                                        [endpoint.orientation.w, endpoint.orientation.x, endpoint.orientation.y, endpoint.orientation.z])
        return self.endpoint

    def pick(self, position):
        if position[2] < 0.2:
            yaw = 80
        else:
            yaw = 30
        self.get_logger().info(f'{position}')
        msg = set_pose_target(position, yaw, [-180.0, 180.0], 1.0)
        res = self.send_request(self.set_pose_target_client, msg)
        if res.pulse:
            servo_data = res.pulse
            set_servo_position(self.joints_pub, 1, ((1, servo_data[0]), ))
            time.sleep(1)
            set_servo_position(self.joints_pub, 1.5, ((1, servo_data[0]),(2, servo_data[1]), (3, servo_data[2]),(4, servo_data[3]), (5, servo_data[4])))
            time.sleep(1.5)
        set_servo_position(self.joints_pub, 0.5, ((10, 540),))
        time.sleep(1)
        position[2] += 0.03

        msg = set_pose_target(position, yaw, [-180.0, 180.0], 1.0)
        res = self.send_request(self.set_pose_target_client, msg)
        if res.pulse:
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
        self.tracker.yaw = 500
        self.tracker.pitch = 150
        self.tracker.pid_yaw.clear()
        self.tracker.pid_pitch.clear()
        self.stamp = time.time()
        self.moving = False

    def main(self):
        while self.running:
            try:
                queue_timeout_s = min(
                    0.1, self.stability_tracker.config.max_target_age_s
                )
                (
                    generation,
                    ros_rgb_image,
                    ros_depth_image,
                    depth_camera_info,
                ) = self.image_queue.get(block=True, timeout=queue_timeout_s)
            except queue.Empty:
                with self.target_state_lock:
                    self.stability_result = self.stability_tracker.evaluate(
                        now_s=self.ros_now_s()
                    )
                if not self.running:
                    break
                else:
                    continue
            observation_timestamp_s = self.image_timestamp_s(ros_rgb_image)
            with self.target_state_lock:
                if not self.observation_guard.accepts(
                    generation, observation_timestamp_s
                ):
                    continue
                tracker = self.tracker
                should_process = (
                    tracker is not None
                    and not self.moving
                    and time.time() > self.start_stamp
                    and self.start
                )
            try:
                rgb_image = np.ndarray(shape=(ros_rgb_image.height, ros_rgb_image.width, 3), dtype=np.uint8, buffer=ros_rgb_image.data)
                depth_image = np.ndarray(shape=(ros_depth_image.height, ros_depth_image.width), dtype=np.uint16, buffer=ros_depth_image.data)
                result_image = np.copy(rgb_image)

                h, w = depth_image.shape[:2]
                depth = np.copy(depth_image).reshape((-1, ))
                depth[depth<=0] = 55555

                sim_depth_image = np.clip(depth_image, 0, 2000).astype(np.float64)

                sim_depth_image = sim_depth_image / 2000.0 * 255.0
                bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)

                depth_color_map = cv2.applyColorMap(sim_depth_image.astype(np.uint8), cv2.COLORMAP_JET)

                if should_process:
                    result_image, p_y, center, r, target_box = tracker.proc(
                        rgb_image,
                        result_image,
                        self.lab_data,
                    )

                    # Stage 1 safety mode: detect and draw only, without moving the arm.
                    if p_y is not None and not self.enable_arm:
                        center_x, center_y = center
                        rgb_h, rgb_w = result_image.shape[:2]
                        center_x = min(max(center_x, 0), rgb_w - 1)
                        center_y = min(max(center_y, 0), rgb_h - 1)
                        cv2.circle(
                            result_image,
                            (int(round(center_x)), int(round(center_y))),
                            5,
                            (255, 255, 255),
                            -1,
                        )
                        localization_result, failure_text = self.localize_target(
                            depth_image,
                            depth_camera_info,
                            target_box,
                        )
                        if (
                            localization_result is not None
                            and localization_result.success
                        ):
                            accepted, stability_result = self._update_stability_for_generation(
                                generation,
                                observation_timestamp_s,
                                position=localization_result.point_color_camera,
                            )
                        else:
                            accepted, stability_result = self._update_stability_for_generation(
                                generation,
                                observation_timestamp_s,
                                position=None,
                                failure=StabilityFailure.LOCALIZATION_FAILED,
                            )
                        if not accepted:
                            continue
                        self.draw_localization_result(
                            result_image,
                            localization_result,
                            failure_text,
                            stability_result,
                        )
                        # 定位结果只用于显示；本阶段无论成功或失败都禁止进入动作路径。
                        p_y = None
                    elif p_y is None and not self.enable_arm:
                        accepted, stability_result = self._update_stability_for_generation(
                            generation,
                            observation_timestamp_s,
                            position=None,
                            failure=StabilityFailure.NO_DETECTION,
                        )
                        if not accepted:
                            continue
                        self.draw_localization_result(
                            result_image,
                            None,
                            StabilityFailure.NO_DETECTION.value,
                            stability_result,
                        )

                    if p_y is not None:
                        set_servo_position(self.joints_pub, 0.02, ((1, int(p_y[1])), (4, int(p_y[0]))))
                        center_x, center_y = center
                        if center_x > w:
                            center_x = w
                        if center_y > h:
                            center_y = h
                        if abs(self.last_pitch_yaw[0] - p_y[0]) < 3 and abs(self.last_pitch_yaw[1] - p_y[1]) < 3:
                            if time.time() - self.stamp > 2:
                                self.stamp = time.time()
                                roi = [int(center_y - 40) - 5, int(center_y - 40) + 5, int(center_x) - 5, int(center_x) + 5]
                                if roi[0] < 0:
                                    roi[0] = 0
                                if roi[1] > h:
                                    roi[1] = h
                                if roi[2] < 0:
                                    roi[2] = 0
                                if roi[3] > w:
                                    roi[3] = w
                                roi_distance = depth_image[roi[0]:roi[1], roi[2]:roi[3]]
                                valid_pixels = roi_distance[np.logical_and(roi_distance > 0, roi_distance < 10000)]

                                if valid_pixels.size > 0:
                                    dist = round(float(np.mean(valid_pixels) / 1000.0), 3)
                                else:
                                    self.get_logger().info('No valid depth data in ROI')
                                    txt = "DISTANCE ERROR !!!"
                                    continue
                                if np.isnan(dist):
                                    txt = "DISTANCE ERROR !!!"
                                    continue
                                # dist -= 0.015 # 物体半径补偿(object radius compensation)
                                dist += 0.01 # 误差补偿(error compensation)
                                K = depth_camera_info.k
                                self.get_endpoint()
                                position = depth_pixel_to_camera((center_x, center_y - 40), dist, (K[0], K[4], K[2], K[5]))
                                
                                position[0] -= 0.01  # rgb相机和深度相机tf有1cm偏移(the RGB camera and depth camera TFs have a 1cm offset)
                                pose_end = np.matmul(self.hand2cam_tf_matrix, common.xyz_euler_to_mat(position, (0, 0, 0)))  # 转换的末端相对坐标(the relative coordinates at the end of the transformation)
                                world_pose = np.matmul(self.endpoint, pose_end)  # 转换到机械臂世界坐标(transform into the world coordinates of the robotic arm)
                                pose_t, pose_R = common.mat_to_xyz_euler(world_pose)
                                self.stamp = time.time()
                                self.moving = True
                                self.get_logger().info(f'{pose_t}')
                                threading.Thread(target=self.pick, args=(pose_t,)).start()
                        else:
                            self.stamp = time.time()
                        dist = depth_image[int(center_y - 40),int(center_x)]
                        if dist < 100:
                            txt = "TOO CLOSE !!!"
                        else:
                            txt = "Dist: {}mm".format(dist)
                        cv2.circle(result_image, (int(center_x), int(center_y)), 5, (255, 255, 255), -1)
                        cv2.circle(depth_color_map, (int(center_x), int(center_y - 40)), 5, (255, 255, 255), -1)
                        cv2.putText(depth_color_map, txt, (10, 400 - 20), cv2.FONT_HERSHEY_PLAIN, 2.0, (0, 0, 0), 10, cv2.LINE_AA)
                        cv2.putText(depth_color_map, txt, (10, 400 - 20), cv2.FONT_HERSHEY_PLAIN, 2.0, (255, 255, 255), 2, cv2.LINE_AA)
                        self.last_pitch_yaw = p_y
                    else:
                        self.stamp = time.time()
                if self.enable_disp:
                    zero_pixels = depth_color_map[sim_depth_image == 0]
                    zero_color = zero_pixels[0] if zero_pixels.size else np.array([0, 0, 0])
                    depth_color_map_padded = cv2.copyMakeBorder(
                        depth_color_map,
                        40,    # 上方填充
                        40, # 下方填充
                        0,              # 左方填充
                        0,              # 右方填充
                        borderType=cv2.BORDER_CONSTANT,
                        value=tuple(map(int, zero_color))  # 填充颜色
                    )
                    result_image = np.concatenate([cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR), depth_color_map_padded, ], axis=1)
                    cv2.imshow("depth", result_image)
                    key = cv2.waitKey(1)
                    if key == ord('q') or key == 27:  # 按q或者esc退出(press q or esc to exit)
                        self.running = False

            except Exception as e:
                self._update_stability_for_generation(
                    generation,
                    observation_timestamp_s,
                    position=None,
                    failure=StabilityFailure.LOCALIZATION_FAILED,
                )
                self.get_logger().info('error1: ' + str(e))
        rclpy.shutdown()

def main():
    node = TrackAndGrabNode('track_and_grab')
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    executor.spin()
    node.destroy_node()

if __name__ == "__main__":
    main()
