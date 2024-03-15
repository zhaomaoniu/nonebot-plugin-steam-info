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

> 记得加上你配置的命令头哦

## 配置
在 .env 文件中配置以下内容

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| STEAM_API_KEY | 无 | Steam API Key，可在 [此处](https://partner.steamgames.com/doc/webapi_overview/auth) 获取 |
| PROXY | 无 | 代理地址 |
| STEAM_REQUEST_INTERVAL | 300 | Steam 请求间隔 & 播报间隔。单位为秒 |

最后再把仓库中 `fonts` 文件夹下的字体文件放到 Bot 的 **运行目录** 下，配置就完毕啦

> 这里使用了 MiSans 字体，感谢 [MiSans](https://hyperos.mi.com/font/zh/)

>如果你希望使用其他字体，请在 `draw.py` 中，将 `font_regular_path`, `font_light_path` 和 `font_bold_path` 修改为你的字体文件路径
