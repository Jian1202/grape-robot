# 项目文档入口

本目录集中保存葡萄机器人项目的治理合同、长期技术参考、问题分析、原始资料和阶段报告。

## 按角色阅读

### 新组员

1. [项目总览与技术路线](reference/01-项目总览与技术路线.md)
2. [葡萄采摘问题分析与实施建议](reports/2026-07-13-葡萄采摘问题分析与实施建议.md)
3. [精选原始资料索引](source-materials/README.md)

### 使用 Codex 的组员

1. 根目录 [AGENTS.md](../AGENTS.md)
2. [Codex 与项目治理入口](governance/README.md)
3. [项目事实基线](governance/PROJECT_FACT_BASE.md)
4. [ROS2 接口合同](governance/ROS2_INTERFACE_CONTRACT.md)
5. [Codex 协作流程](governance/CODEX_WORKFLOW.md)
6. [提示词模板](governance/PROMPT_TEMPLATES.md)

### ROS2 与机械臂组员

1. [ROS2 关键节点与话题](reference/03-ROS2关键节点与话题.md)
2. [机械臂控制接口](reference/04-机械臂控制接口.md)
3. [机械臂动作组文件](reference/05-机械臂动作组文件.md)
4. [SSH 远程接入与安全调试](reference/10-SSH远程接入与安全调试.md)
5. [固定工位基本夹取与真实舵机反馈](reference/11-固定工位基本夹取与真实舵机反馈.md)
6. [ROS2 接口合同](governance/ROS2_INTERFACE_CONTRACT.md)
7. [开发与实车放行关卡](governance/DEVELOPMENT_GATES.md)
8. [固定工位基本夹取只读快照](evidence/basic-fixed-pick-20260719/README.md)
9. [2026-07-19固定工位现场记录与下次交接](reports/2026-07-19-固定工位基本夹取现场记录与下次交接.md)

### YOLO 与现场测试组员

1. [YOLO 数据集与模型](reference/06-YOLO数据集与模型.md)
2. [YOLO 接入与运行维护](reference/08-YOLO接入与运行维护.md)
3. [组员小车安全视觉测试单](reference/09-组员小车安全视觉测试单.md)

## 目录说明

| 目录 | 内容 | 是否代表当前已实现 |
| --- | --- | --- |
| `governance/` | Codex 规则、事实基线、接口合同和实车放行流程 | 是协作规则，不是功能实现 |
| `reference/` | 机器人、ROS2、机械臂和 YOLO 长期参考 | 需要查看每条结论的验证状态 |
| `reports/` | 阶段分析、问题复盘和实施建议 | 建议不等于已经完成 |
| `source-materials/` | 精选厂商手册和课程文件 | 多数为参考资料，部分基于 ROS1 |
| [evidence/](evidence/README.md) | 保存脱敏后的实机接口快照与实验记录 | 只有实际采集后才算证据 |

## 文档之间的关系

```text
原始资料 / 实机输出 / 当前源码
             ↓
        项目事实基线
             ↓
        ROS2 接口合同
             ↓
     设计、实现和开发关卡
             ↓
       报告与 README 展示
```

如果报告、README 和事实基线发生冲突，以更新且有明确证据的事实基线为准，并修正文档链接。

## 使用约定

- 原始资料用于理解厂商方案和确认可能的硬件约束，不代表当前 ROS2 仓库已经实现其中功能。
- ROS1 代码只能参考流程，不能直接覆盖当前 ROS2 实现。
- 涉及机械臂、夹爪和底盘的实验必须分阶段启用。
- 不知道的内容保留为 `UNKNOWN`，不要为了让文档完整而补一个答案。
- 新增或修改外部接口时同步维护接口合同。
- 实机事实变化时同步维护事实基线，并保存日期、设备和验证命令。
