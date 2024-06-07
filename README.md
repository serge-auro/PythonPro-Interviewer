# PythonPro-Interviewer
PythonPro Interviewer is a bot-trainer that will help you prepare for an interview for a Python developer position. The bot asks Python-related questions and checks your answers, helping you sharpen your skills and get ready for real interviews.

## Ключевые технологии
- **Бэкенд:** Python
- **Фронтенд:** telebot для работы с пользователем
- **База данных:** SQLite

## Запуск бота
Для успешной работы бота необходимо создать файл в проекте config.py и указать переменные окружения, пример:
></br>BOT_TOKEN = '123:ABC123'
></br>OPENAI_WHISPER_API_KEY = 'sk-12345'
></br>
></br>SYSTEM_PROMPT = SYSTEM_PROMPT_ = ('You are an evaluator. Please respond in Russian to each input with a strict format: "<Верно/Неверно> || <Comment>". Where "<Верно/Неверно>" is either "Верно" or "Неверно" based on the evaluation of the input, "||" is a separator, and "<Comment>" is a large brief comment explaining the evaluation, up to 3000 characters. Consider that the interviewee is a Junior Python Developer. Provide motivation to Junior Python Developer. ')
></br>
></br>WHISPER_PROMPT = WHISPER_PROMPT = ('Jupyter, Anaconda, PostgreSQL, MySQL, SQLite, Redis, MongoDB, GraphQL, Jenkins, TravisCI, CircleCI, GitLab, Bitbucket, Heroku, DigitalOcean, Netlify, Vercel, Shell, PowerShell, CommandLine, CLI, IDE, VSCode, IntelliJ, DevOps, CI/CD, UnitTesting, TDD, BDD, Cypress, Mocha, Jest, Chai, Jasmine, Webpack, Babel, ESLint, Prettier, Flask, Django, TensorFlow, PyTorch, SciPy, Keras, OpenCV, ScikitLearn, FastAPI, Celery, Docker, AWS, Azure, Lambda, Serverless, Terraform, Ansible, SOLID, DRY, KISS, YAGNI, MVC, MVT, ORM, CRUD, JWT, OAuth, SSL, TLS, PEP8, PEP20, PyPI, Conda, Pipenv, Poetry')


## Инструкция разворачивания на сервере:
#### Обновление списка пакетов
>sudo apt update
#### Установка pip
>sudo apt install python3-pip
#### Установка virtualenv для Python 3.8
>sudo apt install python3.8-venv
#### Клонирование репозитория
>git clone https://github.com/serge-auro/PythonPro-Interviewer.git
#### Переход в директорию проекта
>cd PythonPro-Interviewer/
##### Создание виртуального окружения
>python3 -m venv .venv
##### Активация виртуального окружения
>source .venv/bin/activate
##### Создание файла конфигурации
##### (предполагается, что содержимое config.py у вас уже есть и вы его добавите самостоятельно)
##### Установка необходимых пакетов
>pip install --upgrade pip
</br>
>pip install requests openai numpy ffmpeg-python telebot schedule
##### Установка ffmpeg
>sudo apt install ffmpeg
##### Запустить в репозитории: python3 init_db.py
##### Запустить в репозитории: python3 db_from_csv.py

## Credits
- Developed by:
aureolu@gmail.com
jous@bk.ru
12345-70@mail.ru
lizatrushina96@gmail.com
maxbarkov@bk.ru
ogonkov.aleksei@gmail.com
oip_@inbox.ru
sentr777@bk.ru

### License
This project is licensed under the [Apache-2.0 license](http://www.apache.org/licenses).