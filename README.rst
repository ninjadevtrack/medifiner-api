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
7. To populate states, counties, zipcodes and medications (only for MVP) run the following commands:
	- `docker-compose -f dev.yml run django python manage.py populate_states`
	- `docker-compose -f dev.yml run django python manage.py populate_counties`
	- `docker-compose -f dev.yml run django python manage.py populate_zipcodes`
	- `docker-compose -f dev.yml run django python manage.py populate_medications`
	- `docker-compose -f dev.yml run django python manage.py relate_counties_zipcodes`
	- `docker-compose -f dev.yml run django python manage.py import_population`
8. To import information from vaccinefinder run:
	- `docker-compose -f dev.yml run django python manage.py vaccinefinder_import`
9. Api urls is /api/v1/
10. Run `docker-compose -f dev.yml run django py.test` to run tests
