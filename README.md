# Nonebot-Plugin-Steam-Info
✨ Steam 好友状态播报 NoneBot 插件 ✨

## 功能
- [x] 绑定 Steam ID
- [x] 群友状态变更播报
- [x] 主动查询群友状态

## 使用
steambind [Steam ID 或 Steam好友代码] -绑定 Steam   
steaminfo -查看绑定信息   
steamcheck -查询群友 Steam 状态   
steamupdate [名称] [图片] -更新群聊头像和名称   

## 配置
在 .env 文件中配置以下内容

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| STEAM_API_KEY | 无 | Steam API Key，可在 [此处](https://partner.steamgames.com/doc/webapi_overview/auth) 获取 |
| PROXY | 无 | 代理地址 |
| STEAM_REQUEST_INTERVAL | 300 | Steam 请求间隔 & 播报间隔。单位为秒 |

将仓库克隆到本地，把仓库中的 `nonebot_plugin_steam_info` 文件夹放到你的 NoneBot **插件**目录下，再将仓库中的 `res` 和 `fonts` 文件夹放到你的 NoneBot **启动**目录下。这时再运行你的 NoneBot，插件就会被加载了。
