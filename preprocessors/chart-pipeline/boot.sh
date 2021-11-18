#!/bin/sh
exec gunicorn -b 0.0.0.0:5000 chart:app