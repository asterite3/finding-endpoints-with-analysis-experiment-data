#!/bin/bash

docker run -p 100.72.55.11:8788:80 -v `pwd`/wivet:/var/www/html  --rm php:7.2-apache
