"""Dynamic search strategy generation — LLM plans optimal Amap POI queries.

Instead of 5 hardcoded categories, the LLM generates targeted search queries
based on the specific city, trip duration, and user preferences.
"""

SEARCH_STRATEGY_PROMPT = """你是一个旅游搜索策略专家。为指定城市的{{days}}日游生成最优的高德POI搜索计划。

城市：{{city}}
天数：{{days}}
偏好：{{preferences}}
{{guide_tips}}

请列出最多10个搜索策略，每个包含：
- category: 高德POI类型（如"风景名胜"、"博物馆"、"公园"等）
- keyword: 具体关键词或留空（如"故宫"）

策略设计原则：
1. 覆盖该城市的核心景点类型（风景名胜、博物馆 必选）
2. 根据城市特色补充——北京加胡同/皇家园林，上海加外滩/老洋房，成都加火锅/茶馆，杭州加西湖周边/寺庙
3. 根据天数调整——天数多可加周边/郊区，天数少聚焦核心区
4. 根据偏好定制——美食偏好加餐厅类型，文艺偏好加美术馆/创意园区
5. 避免无意义搜索——不搜火车站/机场/停车场
6. 每天的POI数量需要匹配城市规模——北京上海6-8个/天，小城市3-5个/天

返回纯JSON数组（不要markdown代码块）：
[{{"category": "风景名胜", "keyword": ""}}, {{"category": "博物馆", "keyword": ""}}]"""
