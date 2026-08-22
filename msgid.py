"""
300英雄宅基地自动任务工具 - 接口消息ID常量
取自前端源码枚举，注意：枚举名与服务器实际用途存在大量误导（如 GET_BAG_LIST 实际是领奖），
这里以实际用途注释为准
"""

# ==================== 账号相关 ====================
ACCOUNT_LOGIN = 1004            # 验证Token / 登录
GET_ROLE_INFO = 1009            # 查询战绩（参数: AccountID/Guid/RoleName/RoleID）
GET_USER_INFO = 1011            # 查询历史战绩（参数: RoleID/MatchType/SearchIndex）
GET_TASK_LIST = 1072            # 获取任务列表（每日随机下发 task_config/task_info/daily_sign）
RECEIVE_TASK_REWARD = 1073      # 签到（领取签到礼包，仅 unique_id）
GET_BAG_LIST = 1074             # 领取任务奖励（task_id_list 支持逗号分隔批量）
TASK_ACTION = 1116              # 任务动作（action 区分，如 resonance_game）

# ==================== 帖子相关 ====================
PUBLISH_POST = 1017             # 发帖
LIKE_POST = 1018                # 点赞/取消点赞（like_type: 1=赞 2=取消）
GET_PERSONAL_POSTS = 1028       # 评论/回复帖子
GET_FANS_LIST = 1027            # 我的发布列表（枚举名误导，参数: unique_id+other_unique_id+pages）
GET_USER_DETAIL = 1032          # 我的关注列表（枚举名误导，之前误用于"我的发布"）
GET_POST_LIST = 1033            # 获取帖子列表（社区，响应为对象，id=帖ID userInfo.uid=作者）
GET_POST_DETAIL_CACHE = 1056    # 浏览帖子（post_id）
DELETE_POST_REPLY_DETAIL = 1085 # 删除（type=1 删帖 / 2、3 删回复，value=ID）

# ==================== 社交相关 ====================
GET_PERSONAL_INFO = 1029        # 关注/取消关注（follow_id + follow_type 1/2）

# ==================== 商城相关 ====================
GET_STORE_LIST = 1068           # 购买道具（shop_item_id + address_id）

# 写操作接口：超时后不确定是否已执行，网络层不对其做"超时重试"，防止重复执行
WRITE_MSGIDS = {
    PUBLISH_POST,                # 发帖
    LIKE_POST,                   # 点赞
    GET_PERSONAL_POSTS,          # 评论
    GET_PERSONAL_INFO,           # 关注
    GET_STORE_LIST,              # 购买
    RECEIVE_TASK_REWARD,         # 签到
    GET_BAG_LIST,                # 领奖
    DELETE_POST_REPLY_DETAIL,    # 删除
    TASK_ACTION,                 # 任务动作（共鸣引擎）
}
