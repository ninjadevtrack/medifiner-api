=========================
MEDFINDER API
=========================

***************
Installation
***************
To start project:

1. Install latest version of docker-engine and docker-compose.
2. Change your configuration in a locally created .env file, and change dev.yml for locally configuration.
3. Run `docker-compose -f dev.yml build` to build the project.
4. Run `docker-compose -f dev.yml run django python manage.py migrate` to run migrations.
5. Run `docker-compose -f dev.yml up` to start the server.
6. Api urls will be at /api/v1/.
