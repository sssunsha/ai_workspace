---
source: spartacus
type: code
last-updated: 2026-06-14
---

## 对外暴露的接口/类型

本页聚合 Spartacus 对外消费者（集成商、二次开发者）暴露的主要 API 契约，来源于 `index.ts`、`public_api.ts`、`schema.ts` 等接口定义文件。

---

## 安装与脚手架 API（Schematics）

### `ng add @spartacus/schematics`（SpartacusOptions）

| 字段 | 类型 | 用途 |
|------|------|------|
| `baseUrl` | string | SAP Commerce OCC 后端基础地址，必填 |
| `occPrefix` | string | OCC API 路径前缀，默认 `/occ/v2/` |
| `baseSite` | string | Commerce 站点标识符 |
| `featureLevel` | string | 功能级别（控制渐进式功能启用范围） |
| `theme` | string | 主题名称（sparta / santorini / lambda） |
| `ssr` | boolean | 是否启用服务端渲染（Angular SSR） |
| `language` / `currency` / `urlParameters` | string | 默认语言、货币及 URL 参数配置 |

调用方式：`ng add @spartacus/schematics`，交互式询问上述参数。

---

### `ng generate @spartacus/schematics:add-cms-component`（CxCmsComponentSchema）

用于生成 Spartacus CMS 组件的 Angular CLI Schematic。在 `AngularComponentSchema`（标准组件参数）基础上增加：

| 字段 | 默认值 | 用途 |
|------|--------|------|
| `declareCmsModule` | — | 声明组件的目标模块；省略时自动新建模块 |
| `cmsComponentData` | `true` | 是否注入 `CmsComponentData` 泛型服务 |
| `cmsComponentDataModel` | — | `CmsComponentData<T>` 的泛型参数类型名 |
| `cmsComponentDataModelPath` | `@spartacus/storefront` | 泛型模型的导入路径 |

---

### Wrapper Module Schematic（WrapperModule Schema）

用于为 Spartacus 功能模块生成或定位对应的"包装模块"，典型场景：懒加载时组合多个 feature 模块。

| 字段 | 是否必填 | 用途 |
|------|----------|------|
| `project` | 必填 | 目标 Angular 项目名 |
| `markerModuleName` | 必填 | 作为参照标记的现有模块名 |
| `featureModuleName` | 必填 | 需要加入包装模块的功能模块名 |
| `debug` | 可选 | 打印详细处理日志 |

---

## 构建期环境变量（BuildProcess Env Flags）

在 `buildProcess` 全局对象上注入，控制 storefrontapp 中各集成功能的启用状态。

| 变量 | 类型 | 用途 |
|------|------|------|
| `CX_BASE_URL` | string | 后端 OCC API 基础 URL（覆盖默认值） |
| `CX_B2B` | boolean | 启用 B2B 功能集 |
| `CX_CDS` | boolean | 启用 Commerce Data Solutions 集成 |
| `CX_CDC` | boolean | 启用 SAP Customer Data Cloud 集成 |
| `CX_CDP` | boolean | 启用 SAP Customer Data Platform 集成 |
| `CX_CPQ` | boolean | 启用 CPQ 报价集成 |
| `CX_DIGITAL_PAYMENTS` | boolean | 启用数字支付集成 |
| `CX_EPD_VISUALIZATION` | boolean | 启用 EPD 产品可视化集成 |
| `CX_S4OM` | boolean | 启用 S/4HANA Order Management 集成 |
| `CX_OPF` | boolean | 启用 Open Payment Framework 集成 |
| `CX_OMF` | boolean | 启用 Order Management Foundation 集成 |
| `CX_SEGMENT_REFS` | boolean | 启用 Segment References 集成 |
| `CX_OPPS` | boolean | 启用 OPPS 集成 |
| `CX_MY_ACCOUNT_V2` | boolean | 启用 My Account V2 UI |
| `CX_PDF_INVOICES` | boolean | 启用 PDF 发票功能 |
| `CX_PUNCHOUT` | boolean | 启用 Punchout 集成 |
| `CX_REQUESTED_DELIVERY_DATE` | boolean | 启用要求交货日期功能 |
| `CX_ESTIMATED_DELIVERY_DATE` | boolean | 启用预估交货日期功能 |
| `CX_S4_SERVICE` | boolean | 启用 S4 Service 集成 |

---

## Cypress E2E 无障碍测试扩展 API（a11y Continuum）

扩展 Cypress `Chainable` 接口，供 E2E 测试使用 Level Access Continuum SDK 做可访问性检查。

| 命令 | 参数 | 用途 |
|------|------|------|
| `cy.a11yContinuumSetup(configPath?)` | 可选配置文件路径 | 初始化 Continuum SDK，加载引擎和规则集 |
| `cy.a11yRunContinuumTest(failIfConcerns?, includeIframe?)` | 两个布尔值，默认均为 `true` | 对当前 DOM（或指定元素）运行无障碍扫描；发现问题默认断言失败 |
| `cy.a11YContinuumPrintResults()` | — | 将问题输出到 Cypress 日志并高亮违规元素 |
| `cy.a11YContinuumFailIfConcerns()` | — | 存在任何无障碍问题时强制断言失败 |
| `cy.disableBestPractices(ids: number[])` | 规则 ID 数组 | 按 ID 禁用特定最佳实践规则，用于过滤误报 |

---

## 内部工具 API（tools/）

仅供仓库内部脚本使用，不对外消费者开放，但记录于此作为维护参考。

### tools/config — 配置一致性检查工具

| 类型/函数 | 用途 |
|----------|------|
| `ProgramOptions` | CLI 模式枚举：`fix`（修复 tsconfig/依赖版本）、`bumpVersions`（大版本升级）、`generateDeps`（重新生成依赖声明） |
| `Library.entryPoints[]` | 描述库的所有入口点（名称、相对目录、入口文件），用于 tsconfig paths 一致性验证 |
| `error(file, errors[], help[])` | 格式化错误日志输出（红色） |
| `warning(file, warnings[], help[])` | 格式化警告日志输出（黄色） |

### tools/eslint-rules — 自定义 ESLint 规则

Spartacus 仓库级自定义规则，通过 `@nx/workspace-*` 命名空间引用：

| 规则名 | 作用 |
|--------|------|
| `use-provide-default-config(-factory)` | 强制使用 Spartacus 标准 config 提供方式 |
| `use-provide-default-feature-toggles(-factory)` | 强制使用标准 feature toggle 提供方式 |
| `no-ngrx-fail-action-without-error-action-implementation` | NgRx fail action 必须实现 `ErrorAction` 接口 |
| `ngrx-fail-action-must-initialize-error` | NgRx fail action 构造时必须初始化 `error` 字段 |
| `no-const-enum` | 禁止 TypeScript `const enum`（影响库的打包兼容性） |
| `feature-config-service-must-be-private` | `FeatureConfigService` 注入必须声明为 `private` |
| `no-self-public-api-import` | 禁止库内部从自身的 public API 路径循环引用 |

### tools/chalk — 终端样式工具

内部替代 chalk 库，提供 `red`、`yellow`、`blue`、`gray`、`green`、`bold` 方法，接受可选字符串，返回带 ANSI 转义码的字符串。

---

## 全局 TypeScript 类型补丁

**文件：** `types.d.ts`（仓库根）

为 `GlobalEventHandlersEventMap` 添加模板字面量索引签名 `` `keydown.${string}` ``，映射为 `KeyboardEvent`。

**目的：** 解决 Angular 编译器在 `typeCheckHostBindings` 启用时对 `@HostListener('keydown.Enter')` 语法报类型错误的已知问题（Angular Issue #63170、#40778）。此补丁无用户可配置项，属于环境类型声明。
