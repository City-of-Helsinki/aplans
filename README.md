# aplans

aplans is a service for administrating and monitoring action plans. It has the following components:

- admin UI for modifying action plan content
- REST API for distributing the information

The service was first used to implement monitoring for the [Carbon-neutral Helsinki 2035 action plan](https://www.stadinilmasto.fi/files/2018/03/Executive_summary_HNH2035.pdf). The [ReactJS UI code](https://github.com/City-of-Helsinki/cnh-ui) is also open source.

## Installation

### Development

Install the required Python packages:

```shell
pip install -r requirements.txt
```

Create a file called `local_settings.py` in your repo root with the following contents:

```python
DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aplans',
        'ATOMIC_REQUESTS': True,
    }
}
```

Make sure you have created a Postgres database with the same name (here `aplans`).

Create a superuser:

```shell
python manage.py createsuperuser
```

Compile the translation files:

```shell
python manage.py compilemessages
```

### Production

The project is containerized using Docker Compose. You will still need to set some
variables in your environment; see the first few lines in `aplans/settings.py`.

## Contributing

### Python requirements

This project uses two files for requirements. The workflow is as follows.

`requirements.txt` is not edited manually, but is generated
with `pip-compile`.

`requirements.txt` always contains fully tested, pinned versions
of the requirements. `requirements.in` contains the primary, unpinned
requirements of the project without their dependencies.

In production, deployments should always use `requirements.txt`
and the versions pinned therein. In development, new virtualenvs
and development environments should also be initialised using
`requirements.txt`. `pip-sync` will synchronize the active
virtualenv to match exactly the packages in `requirements.txt`.

In development and testing, to update to the latest versions
of requirements, use the command `pip-compile`. You can
use [requires.io](https://requires.io) to monitor the
pinned versions for updates.

To remove a dependency, remove it from `requirements.in`,
run `pip-compile` and then `pip-sync`. If everything works
as expected, commit the changes.


## Attribution

City of Helsinki would like to request that when this source code is forked
and deployed to production use for another organization, the following phrases
would be added to the FAQ or similar section of the user-visible UI, as well as
to the public presentations or other materials presenting the new service:

> [Name of the service] is an open-source service based on [Helsinki Climate Watch](https://github.com/City-of-Helsinki/cnh-ui),
> a service developed by the City of Helsinki. Helsinki Climate Watch has
> received funding from the European Union EIT Climate-KIC programme.

Or in Finnish:

> Palvelu on avointa lähdekoodia ja perustuu alun perin Helsingin kaupungin kehittämään [Helsingin ilmastovahti -palveluun](https://github.com/City-of-Helsinki/cnh-ui).
> Helsingin ilmastovahti on saanut tukea EU:n Climate-KIC-ohjelmasta.
