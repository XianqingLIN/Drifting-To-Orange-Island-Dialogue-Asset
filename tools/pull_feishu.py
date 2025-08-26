import os, requests, yaml, json
APP_ID     = os.getenv('FEISHU_APP_ID')
APP_SECRET = os.getenv('FEISHU_APP_SECRET')
TABLE_ID   = os.getenv('FEISHU_TABLE_ID')

# 1. 获取 tenant_access_token
token = requests.post(
    'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    json={'app_id': APP_ID, 'app_secret': APP_SECRET}
).json()['tenant_access_token']

# 2. 取整张表
url = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{TABLE_ID}/values/dialog!A1:Z1000'
data = requests.get(url, headers={'Authorization': f'Bearer {token}'}).json()
records = data['data']['valueRange']['values'][1:]  # 跳过表头

# 3. 校验 schema & 导出 .json / .bytes …
...