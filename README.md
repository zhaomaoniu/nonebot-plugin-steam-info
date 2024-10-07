# Nonebot-Plugin-Steam-Info
✨ Steam 好友状态播报 NoneBot 插件 ✨

## 介绍

这是一个基于 NoneBot2 的 Steam 好友状态播报插件，拥有绑定 Steam ID，查询群友状态，展示个人 Steam 主页等功能，支持跨平台，画图部分 100% 使用 Pillow 实现，较无头浏览器渲染更加轻量高效

## 功能
- [x] 绑定 Steam ID
- [x] 群友状态变更播报
- [x] 群友游戏时间播报
- [x] 主动查询群友状态
- [x] 展示个人 Steam 主页

## 预览
仿照了 Steam 好友列表的样式

图 1. 部分播报
![image](./preview.png)

图 2. 全部播报
![image](./preview_1.png)

图 3. 个人 Steam 主页
![image](./preview_2.png)


## 使用
| 命令 | 别名 |  说明 |
| --- | --- | --- |
| steambind [Steam ID 或 Steam好友代码] | 绑定steam | 绑定 Steam |
| steamunbind | 解绑steam | 解绑 Steam |
| steaminfo (可选)[@某人 或 Steam ID 或 Steam好友代码] | steam信息 | 查看个人主页 |
| steamcheck | 查看steam, 查steam | 查询群友 Steam 状态 |
| steamupdate [名称] [图片] | 更新群信息 | 更新群聊头像和名称 |
| steamenable | 启用steam | 启用群友状态播报 |
| steamdisable | 禁用steam | 禁用群友状态播报 |
| steamnickname [昵称] | steam昵称 | 设置 Steam 玩家昵称，用于辨识 Steam 名称与群昵称不一致的群友 |

> 记得加上你配置的命令头哦

## 安装方法
<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-steam-info

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot-plugin-steam-info
</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-steam-info
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-steam-info
</details>
<details>
<summary>conda</summary>

    conda install nonebot-plugin-steam-info
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_steam_info"]

</details>




## 配置
在 .env 文件中配置以下内容

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| STEAM_API_KEY | 无 | Steam API Key，可以是一个字符串，也可以是一列表的字符串，即支持多个API Key，在 [此处](https://partner.steamgames.com/doc/webapi_overview/auth) 获取 |
| PROXY | 无 | 代理地址 |
| STEAM_REQUEST_INTERVAL | 300 | Steam 请求间隔 & 播报间隔。单位为秒 |
| STEAM_BROADCAST_TYPE | `"part"` | 播报类型。`"part"` 为部分播报(图 2)，`"all"` 为全部播报(图 1)，`"none"` 为只播报文字消息 |
| STEAM_DISABLE_BROADCAST_ON_STARTUP | `False` | Bot 启动时是否禁用播报 |
| STEAM_FONT_REGULAR_PATH | fonts/MiSans-Regular.ttf | Regular 字体相对目录 |
| STEAM_FONT_LIGHT_PATH | fonts/MiSans-Light.ttf | Light 字体相对目录 |
| STEAM_FONT_BOLD_PATH |fonts/MiSans-Bold.ttf | Bold 字体相对目录 |

最后再把仓库中 `fonts` 文件夹放到 Bot 的 **运行目录** 下，配置就完毕啦

在默认配置下，项目结构大致如下：
```
your_project/
├── bot.py
├── .env.*
├── fonts/
│   ├── MiSans-Regular.ttf
│   ├── MiSans-Light.ttf
│   └── MiSans-Bold.ttf
└── ...
```

> 这里使用了 MiSans 字体，感谢 [MiSans](https://hyperos.mi.com/font/zh/)

> 如果你希望使用其他字体，请参考配置版块。

> 如果配置中不填写 `font/`，则会在`your_project/`下寻找字体文件。