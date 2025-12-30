# Agent Task File

## Project: room_hvac (Home Assistant Integration)

### Agent Role Assumption

你是一个熟悉 Home Assistant Core、自定义 integration、`climate` 平台、Config Flow 与事件模型的高级 Python 工程师。
你的目标是严格按照规格实现 `room_hvac`，不得引入未定义的新功能或行为假设。

---

## Milestone 0 – 规格冻结与工程初始化

### Task 0.1 – 规格理解与约束确认

**Objective**
确保对 room_hvac 的功能边界与设计假设理解完全一致。

**Instructions**
完整阅读 room_hvac 的 Functional Spec 与 Config Flow 说明，输出一份不超过 1 页的技术理解摘要，内容必须包含：

* room_hvac 的核心职责
* 明确的非目标行为
* 支持的 HVAC 模式与路由规则
* preset 的两套体系及其作用范围
* 强制模式（Force Control Mode）的行为边界

**Deliverable**
一份结构化文字摘要，用作实现过程中的最高约束说明。

---

### Task 0.2 – Integration 基础结构初始化

**Objective**
创建一个最小但规范的 Home Assistant integration 工程结构。

**Instructions**
创建自定义 integration `room_hvac`，至少包含以下文件：

* manifest.json
* **init**.py
* climate.py
* config_flow.py
* const.py

manifest.json 中需正确填写：

* domain = room_hvac
* name
* version
* config_flow = true

其余字段保持最小可用集合。

**Deliverable**
一个可被 Home Assistant 识别并加载的 integration 目录结构。

---

## Milestone 1 – Climate 实体骨架

### Task 1.1 – 常量与内部枚举定义

**Objective**
集中管理所有枚举与关键常量，避免魔法值散落。

**Instructions**
在 const.py 中定义：

* DOMAIN
* 支持的 hvac_mode 列表
* 空调类模式集合（cool / dry / fan_only）
* 地暖类模式集合（heat）
* preset slot 的内部标识（例如 slot_1 ~ slot_4）

命名需清晰、稳定，便于后续扩展。

**Deliverable**
完整且可被后续模块引用的 const.py。

---

### Task 1.2 – ClimateEntity 基础实现

**Objective**
让 room_hvac 作为一个 climate 实体成功注册并展示。

**Instructions**
在 climate.py 中实现 RoomHVACClimateEntity：

* 继承 ClimateEntity
* 实现 name、unique_id
* 声明 supported_features
* 声明 hvac_modes
* 默认 hvac_mode = off

此阶段不允许实现任何下游控制逻辑。

**Deliverable**
Home Assistant UI 中可见的 room_hvac climate 实体。

---

### Task 1.3 – 实体加载与注册

**Objective**
完成 config entry 到实体实例的完整加载链路。

**Instructions**
在 **init**.py 与 climate.py 中完成 setup_entry 逻辑，
确保 config entry 创建后可以正确加载 room_hvac 实体。

**Deliverable**
配置完成后实体自动出现，无需重启。

---

## Milestone 2 – Config Flow 完整实现

### Task 2.1 – Step 1：选择下游 Climate 实体

**Objective**
让用户选择空调与地暖执行器。

**Instructions**
在 config_flow.py 中实现第一步：

* 选择空调 climate 实体
* 选择地暖 climate 实体

校验：

* 两个 entity_id 不得相同
* domain 必须是 climate

错误提示需明确。

**Deliverable**
一个可提交、可校验的实体选择步骤。

---

### Task 2.2 – 下游能力探测与校验

**Objective**
防止用户选择不具备必要能力的实体。

**Instructions**
在实体选择完成后读取其 state attributes：

* 空调：是否支持 fan_mode，是否存在 fan_modes
* 地暖：是否支持 heat 模式与 target_temperature

不满足最低要求则中断流程并报错。

**Deliverable**
具备能力校验的安全 Config Flow。

---

### Task 2.3 – Step 2：基础行为选项

**Objective**
配置全局行为策略。

**Instructions**
实现第二步表单，仅包含：

* 强制模式（布尔值，Force Control Mode）

将结果保存至 config entry data。

**Deliverable**
包含 force_mode 配置的数据结构。

---

### Task 2.4 – Step 3：空调 Preset 配置

**Objective**
配置空调类模式使用的 preset。

**Instructions**
提供 4 个 preset slot，每个 slot 支持：

* 名称
* 图标
* 风速（来源于空调 fan_modes）

规则：

* 未配置风速的 slot 直接忽略
* 不强制至少配置一个 slot

**Deliverable**
结构清晰的空调 preset 配置数据。

---

### Task 2.5 – Step 4：地暖 Preset 配置

**Objective**
配置制热模式使用的 preset。

**Instructions**
提供 4 个 preset slot，每个 slot 支持：

* 名称
* 图标
* 目标温度

校验温度合理性（结合地暖 min/max）。

**Deliverable**
结构清晰的地暖 preset 配置数据。

---

### Task 2.6 – Step 5：确认与创建 Entry

**Objective**
完成配置并生成 config entry。

**Instructions**
展示配置摘要并在确认后创建 config entry，
不允许在此步骤继续修改内容。

**Deliverable**
完整、可用于初始化实体的 config entry。

---

## Milestone 3 – 模式路由与下游控制

### Task 3.1 – hvac_mode 路由逻辑

**Objective**
实现模式与执行器的明确映射。

**Instructions**
实现 hvac_mode 设置逻辑：

* cool / dry / fan_only → 空调
* heat → 地暖
* off → 全部关闭

切换时必须关闭非目标设备。

**Deliverable**
稳定、可预测的模式切换行为。

---

### Task 3.2 – 目标温度下发

**Objective**
支持 room_hvac 作为真正的温控器。

**Instructions**
实现 set_temperature：

* cool / dry / heat → 直接下发
* fan_only → 忽略但不报错

不实现历史恢复逻辑。

**Deliverable**
目标温度正确作用于当前执行器。

---

### Task 3.3 – 当前温度映射

**Objective**
正确反映房间当前温度。

**Instructions**
实现 current_temperature：

* 返回当前执行器的温度
* 允许模式切换导致来源跳变

**Deliverable**
UI 中可接受的温度展示行为。

---

## Milestone 4 – Preset 行为与动态 UI

### Task 4.1 – 动态 preset_modes

**Objective**
让 UI 中的 preset 列表随模式变化。

**Instructions**
实现 preset_modes：

* 空调类模式 → 空调 preset
* heat → 地暖 preset
* off → 空列表

**Deliverable**
与模式严格一致的 preset UI。

---

### Task 4.2 – Preset 激活逻辑

**Objective**
让 preset 产生实际控制效果。

**Instructions**
实现 set_preset_mode：

* 空调 preset → 设置 fan_mode
* 地暖 preset → 设置目标温度

不改变 hvac_mode，不保存历史。

**Deliverable**
preset 行为与规格完全一致。

---

## Milestone 5 – 强制模式与状态一致性

### Task 5.1 – 下游状态监听

**Objective**
感知外部对空调 / 地暖的修改。

**Instructions**
监听两个下游 climate 的 state_changed 事件，
能够区分本 entity 操作与外部操作。

**Deliverable**
可靠的状态监听基础。

---

### Task 5.2 – 强制模式回写纠错

**Objective**
保证强制模式下的一致性。

**Instructions**
在 force_mode 启用时：

* 检测不一致状态
* 立即回写纠正
* 失败直接抛异常，不降级

**Deliverable**
严格的主从控制行为。

---

### Task 5.3 – 循环保护机制

**Objective**
避免回写引发死循环。

**Instructions**
引入 context 或内部标记，
确保自发操作不会再次触发纠错逻辑。

**Deliverable**
稳定运行的监听与回写机制。

---

## Milestone 6 – 可观测性与收尾

### Task 6.1 – 扩展调试属性

**Objective**
提升可理解性与可维护性。

**Instructions**
为 room_hvac 增加 attributes：

* 当前执行器实体
* 是否启用强制模式
* 当前运行类别（空调 / 地暖）

**Deliverable**
开发者工具中可见的调试信息。

---

### Task 6.2 – 日志与错误策略

**Objective**
便于问题定位。

**Instructions**
为关键路径增加日志：

* 模式切换
* preset 激活
* 强制纠错失败

区分 info / warning / error。

**Deliverable**
清晰、不过量的日志输出。

---

### Task 6.3 – 规格对照自检

**Objective**
确保实现未偏离规格。

**Instructions**
逐条对照 Functional Spec，
列出所有已实现点与任何偏差说明，
形成 v1 发布前检查清单。

**Deliverable**
一份最终实现自检报告。


