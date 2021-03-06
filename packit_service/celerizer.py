# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from datetime import timedelta
from os import getenv

from celery import Celery
from lazy_object_proxy import Proxy

from packit_service.models import get_pg_url
from packit_service.sentry_integration import configure_sentry


class Celerizer:
    def __init__(self):
        self._celery_app = None

    @property
    def celery_app(self):
        if self._celery_app is None:
            bt_options = {}
            if getenv("AWS_ACCESS_KEY_ID") and getenv("AWS_SECRET_ACCESS_KEY"):
                broker_url = "sqs://"
                if not getenv("QUEUE_NAME_PREFIX"):
                    raise ValueError("QUEUE_NAME_PREFIX not set")
                bt_options["queue_name_prefix"] = getenv("QUEUE_NAME_PREFIX")
            else:
                host = getenv("REDIS_SERVICE_HOST", "redis")
                password = getenv("REDIS_PASSWORD", "")
                port = getenv("REDIS_SERVICE_PORT", "6379")
                db = getenv("REDIS_SERVICE_DB", "0")
                broker_url = f"redis://:{password}@{host}:{port}/{db}"

            # https://docs.celeryproject.org/en/stable/userguide/configuration.html#database-url-examples
            postgres_url = f"db+{get_pg_url()}"

            # http://docs.celeryproject.org/en/latest/reference/celery.html#celery.Celery
            self._celery_app = Celery(backend=postgres_url, broker=broker_url)
            self._celery_app.conf.broker_transport_options = bt_options

            days = int(getenv("CELERY_RESULT_EXPIRES", "30"))
            # https://docs.celeryproject.org/en/latest/userguide/configuration.html#result-expires
            self._celery_app.conf.result_expires = timedelta(days=days)

        return self._celery_app


def get_celery_application():
    celerizer = Celerizer()
    app = celerizer.celery_app
    configure_sentry(
        runner_type="packit-worker",
        celery_integration=True,
        sqlalchemy_integration=True,
    )
    return app


celery_app: Celery = Proxy(get_celery_application)
