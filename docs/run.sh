# 相关依赖检查
node -v
npm -v

psql --version

python -m venv venv
source /home/cannot-goodenough/code/ask/venv/bin/activate
pip install -r requirements.txt

# 后端
python manage.py migrate
python manage.py loaddata exercises/fixtures/data.json

# 启动
python manage.py runserver

# 前端
npm install
npm run dev
