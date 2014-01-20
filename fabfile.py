#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import with_statement
from fabric.api import *
from fabric.context_managers import *
from fabric.utils import puts
from fabric.colors import red, green
from cuisine import *

import time

GIT_REPO = 'https://github.com/mobishift2011/baokuan.git'
ENV = None

def production():
    global  ENV
    ENV = 'PRODUCTION'
    puts(red('Using {} settings').format(ENV))
    env.user = 'root'
    env.hosts = [
        # 'ec2-54-199-138-213.ap-northeast-1.compute.amazonaws.com'
        '222.73.105.209'
    ]

def setup_packages():
    puts(green('Installing ubuntu packages'))
    sudo('apt-get update')
    sudo('easy_install pip')
    sudo('pip install setuptools --no-use-wheel --upgrade')
    sudo('apt-get -y install build-essential python-dev libevent-dev libxslt-dev uuid-dev python-setuptools dtach libzmq-dev numactl')
    sudo('apt-get install uwsgi')
    package_ensure('nginx')
    package_ensure('git')
    package_ensure('ufw')
    package_ensure('redis-server')

    # setup_celery()

def configure_redis():
    package_ensure('redis-server')

def setup_folders():
    puts(green('Setting up on-disk folders'))

    with mode_sudo():
        dir_ensure('/srv')
        dir_ensure('/srv/baokuan')

def configure_firewall():
    puts(green('Configuring Firewall'))
    if ENV == 'PRODUCTION':
        sudo('ufw allow proto tcp from any to any port 22')
        sudo('ufw allow proto tcp from any to any port 80')
        sudo('ufw allow proto tcp from any to any port 8000')
        sudo('ufw allow proto tcp from any to any port 9001')
        sudo('ufw --force enable')

def configure_mongodb():
    puts(green('Configuring MongoDB'))
    # sudo('service mongodb stop')
    sudo('numactl --interleave=all mongod --dbpath /var/lib/mongodb &')

def configure_server():
    with cd('/srv/baokuan'):
        with cd('baokuan'):
            # sudo('python manage.py collectstatic')
            sudo('gunicorn_django -w=4 ')

def configure_nginx():
    puts(green('Configuring Nginx web server'))
    
    nginx_conf = text_strip_margin('''
    |user www-data;
    |worker_processes 8;
    |worker_rlimit_nofile 65536;
    |pid /var/run/nginx.pid;
    |
    |events {
    |    use epoll;
    |    worker_connections 4096;
    |    multi_accept on;
    |}
    |
    |http {
    |
    |    ##
    |    # Basic Settings
    |    ##
    |
    |    sendfile on;
    |    tcp_nopush on;
    |    tcp_nodelay on;
    |    keepalive_timeout 65;
    |    types_hash_max_size 2048;
    |    # server_tokens off;
    |
    |    # server_names_hash_bucket_size 64;
    |    # server_name_in_redirect off;
    |
    |    include /etc/nginx/mime.types;
    |    default_type application/octet-stream;
    |
    |    ##
    |    # Logging Settings
    |    ##
    |
    |    access_log /var/log/nginx/access.log;
    |    error_log /var/log/nginx/error.log;
    |
    |    ##
    |    # Gzip Settings
    |    ##
    |
    |    gzip on;
    |    gzip_disable "msie6";
    |
    |    gzip_vary on;
    |    gzip_proxied any;
    |    gzip_comp_level 6;
    |    gzip_buffers 16 8k;
    |    gzip_http_version 1.1;
    |    gzip_types text/plain text/css application/json application/x-javascript text/xml application/xml application/xml+rss text/javascript;
    |
    |    ##
    |    # Real IP in Nginx
    |    ##
    |    
    |    real_ip_header X-Forwarded-For;
    |    set_real_ip_from 0.0.0.0/0;
    |
    |    ##
    |    # Virtual Host Configs
    |    ##
    |
    |    include /etc/nginx/conf.d/*.conf;
    |    include /etc/nginx/sites-enabled/*;
    |}
    |
    ''')

    baokuan_conf = text_strip_margin('''
    |
    |server {
    |    listen   80; ## listen for ipv4; this line is default and implied
    |    server_name luckytao.tk;
    |    access_log /tmp/baokuan_nginx.log;
    |    error_log /tmp/baokuan_nginx_error.log;
    |    client_max_body_size 5m;
    |
    |    location /baokuan/assets {
    |        autoindex on;
    |        alias /srv/baokuan/baokuan/static;
    |    }
    |
    |    location /assets {
    |        autoindex on;
    |        alias /srv/baokuan/baokuan/static;
    |    }
    |
    |    location /baokuan {
    |        #include uwsgi_params;
    |        #uwsgi_pass 127.0.0.1:8000;
    |        proxy_pass http://127.0.0.1:8000;
    |        #uwsgi_pass unix:///tmp/stubbs.sock;
    |        #uwsgi_param X-Real-IP $remote_addr;
    |        #uwsgi_param Host $http_host;
    |    }
    |
    |   location / {
    |       autoindex on;
    |       root /srv/luckytao;
    |   }
    |
    |}
    |
    ''')

    with mode_sudo():
        file_write('/etc/nginx/sites-available/baokuan.conf', baokuan_conf)
        file_write('/etc/nginx/nginx.conf', nginx_conf)

        if file_exists('/etc/nginx/sites-enabled/default'):
            sudo('rm /etc/nginx/sites-enabled/default')

        if not file_exists('/etc/nginx/sites-enabled/baokuan.conf'):
            sudo('ln -s /etc/nginx/sites-available/baokuan.conf /etc/nginx/sites-enabled/baokuan.conf')

        with settings(warn_only=True):
            sudo('service nginx start')
        sudo('service nginx reload')

def sync_latest_code():
    puts(green('Fetching Lastest code From repo'))
    with cd('/srv/baokuan'):
        if dir_exists('/srv/baokuan/src'):
            with cd('/srv/baokuan/src'):
                sudo('git reset HEAD --hard && git fetch --all && git pull')
                if ENV == 'INTEGRATE':
                    sudo('git checkout dev')
                else:
                    sudo('git checkout master')
        else:
            with mode_sudo():
                sudo('git clone %s src' % GIT_REPO)
        sudo('cp -r /srv/baokuan/src/* /srv/baokuan/')
        # sudo('chmod 777 /srv/baokuan/static/CACHE -R')
    
    with cd('/srv/baokuan/src'):
        puts(green('Installing app denpendencies'))
        sudo('pip install -r requirements.txt -i http://pypi.douban.com/simple')

def restart_web_server():
    puts(green('Reloading the service'))
    sudo('/srv/baokuan/manage.sh restart')
    if ENV == 'PRODUCTION':
        with settings(warn_only=True):
            with cd('/srv/baokuan'):
                run('sudo killall supervisord')
                run('sleep 0.5')
                run('sudo supervisord -c supervisord.conf -l /tmp/supervisord.log')

def restart():
    puts(green('Restarting the service'))
    with settings(warn_only=True):
        sudo('killall gunicorn_django')
        with cd('/srv/baokuan'):
            sudo('sudo killall supervisord')
            sudo('sleep 0.5')
            sudo('export ENV={} && export C_FORCE_ROOT="true" && \
                supervisord -c supervisord.conf -l /tmp/supervisord.log'.format(ENV))

    # configure_nginx()
    # configure_server()

def init_data():
    with cd('/srv/baokuan/db'):
        sudo('mongorestore categories')

def deploy():
    """
    Setup environments, configure, and start.
    """
    puts(green('Starting deployment'))
    setup_packages()
    setup_folders()

    configure_firewall()
    sync_latest_code()
    configure_nginx()
    configure_server()
    init_data()
    restart()