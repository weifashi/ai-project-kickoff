# AI 新项目启动技能包

**版本：0.1.0-draft.1 · 草案 · 未安装**

从“我要做一个项目”到可评审、可归档、可验证、可交接的启动方案。
默认采用**轻量 / 标准 / 高风险三档自适应**，涵盖官网、Web/SaaS/后台、移动、桌面、API/CLI/SDK，并按需叠加离线、外设、交易和产品内置LLM风险。

## 从哪里开始

1. AI读取 [项目启动入口](skills/ai-project-kickoff/SKILL.md)，确认平台、档位及本轮交付目标，再按需加载参考。
2. 到方案评审或阶段汇报时读取 [随包html-mockup](skills/html-mockup/SKILL.md)，生成自包含HTML并实际检查；不把预览副本当长期存档。
3. 按需使用 [9份模板](skills/ai-project-kickoff/assets/templates/)，填写实际项目事实；模板存在不代表项目已通过验收。
4. 看 [已接受设计与范围](docs/accepted-design.md)、[验证与限制](docs/validation.md)、[独立场景记录](docs/scenario-evidence.md)、[HTML交付报告](docs/delivery-report.html)。

无需安装也能让AI按仓库文件读取。示例指令：

> 读取 skills/ai-project-kickoff/SKILL.md。我准备做〔项目想法〕，现有团队/平台是〔实际约束〕。按三档自适应流程先完成开工就绪方案，使用包内html-mockup汇报，保留原型与决策档案；暂不安装、部署或调用付费服务。

现有项目沿用已有结构与规则，不自动搬文件、不强换技术栈。计划/设计、实现、提交、推送、安装、迁移和部署遵循各自当前授权。

## 包含什么

```text
skills/
├─ ai-project-kickoff/
│  ├─ SKILL.md
│  ├─ references/
│  └─ assets/templates/
└─ html-mockup/
   ├─ SKILL.md
   ├─ references/
   └─ assets/
docs/
  accepted-design.md
  research-snapshot.json
  validation.md
  delivery-report.html
tests/
```

## 维护规则

- **GitHub是唯一源码**；it-note只存导航、使用说明、版本摘要、固定commit/tag和检查结果，不能形成第二套可独立修改的技能源码。
- 原型、需求和运维等业务档案放在各业务项目中，通用技能仓库只放方法和模板。
- 技术热度参考冻结为 **2026-10-28**，来源见 [选型手册](skills/ai-project-kickoff/references/research-and-selection.md) 和原始快照；未来立项必须复核易变事实。
- 本包不是所有行业、法规或平台的合规认证，也不能保证任意未来项目零遗漏。
- 以当前授权保留为私有仓库；不得因“放到GitHub”自行公开资料。整体内容没有在此声明新的统一开源许可，随包第三方/源素材分别遵循其许可和来源记录。

本仓库保存草案不等于已安装。不要在未获得新请求时复制到任何客户端技能目录、修改全局规则或同步其他机器。
