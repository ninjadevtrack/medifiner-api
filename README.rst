=========================
MEDFINDER API
=========================

***************
Installation
***************
To start project using:

1. Install docker-engine and docker-compose in your machine to the last version.
2. Change your configuration in a locally created .env file, and change dev.yml for locally configuration.
3. Run docker-compose -f dev.yml build to build the project.
4. Run docker-compose -f dev.yml run django python manage.py migrate to create the necessary first migration.
5. Run docker-compose -f dev.yml up to start the server in your local machine.
6. Api urls will be at /api/v1/.