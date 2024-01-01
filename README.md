### ***NOTE It's not a complete version yet***.

# Software requirements.
- python 3.10^
- docker

# ENV Example.
```env
EMAIL=
PASS=
MAIN_GROUP_ID=
```

# Usage python script.
## Create a virtual environment.
```bash
python -v venv pyenv
```
```bash
/pyenv/Script/activate
```
## Run selenium stand alone with docker-compose.
```bash
cd /scraping_comments_from_group_fb
```
```
docker-compose up -d
```
## Run python script.
```bash
python main.py
```
