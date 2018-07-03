=========================
MEDFINDER API
=========================

***************
Installation
***************
To start project:

1. Install latest version of docker-engine and docker-compose
2. Copy `env.sample` into new `.env` file
3. Run `docker-compose -f dev.yml build` to build the project
4. Run `docker-compose -f dev.yml run django python manage.py migrate` to run pending migrations
5. Run `docker-compose -f dev.yml run django python manage.py createsuperuser` to create super user
6. Run `docker-compose -f dev.yml up` to start the local server
7. Api urls is /api/v1/
