大学社团管理系统
==============

一个简单的大学社团管理系统.

设置flask app:
-------------
.. code-block:: text

    $ export FLASK_APP=flasky.py

初始化数据库:
-----------

.. code-block:: text

    $ python setup.py


填写配置信息:
-----------
    根据.env_demo的格式填写配置信息并且保存为.env
.. code-block:: text

    MAIL_USERNAME=xxx@xxx.com
    MAIL_PASSWORD=yyy

生成测试数据:
-----------

.. code-block:: text

    $ flask shell
    >>> fake.init()
    >>> exit()

运行
---

..code-block:: text

    flask run