使用说明
========

安装依赖
--------

    $ sudo apt install python3-pip
    $ pip3 install sphinx
        # 如果执行失败，可以采用以下命令
        # python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple sphinx
        # 或者手动在以下网站下载sphinx_rtd_theme-3.0.2-py2.py3-none-any.whl，然后安装本地文件 pip install ./sphinx_rtd_theme-3.0.2-py2.py3-none-any.whl 
        # https://pypi.org/project/sphinx-rtd-theme/#files
    $ pip3 install sphinx_rtd_theme

💡 **Note:**  在 Ubuntu 24.04 或其他启用了 externally-managed-environment 的系统中，Python 使用此机制保护系统环境，防止直接使用 pip 安装包破坏系统依赖。
          如果以上命令在执行中报错，可以在命令行后面添加 --break-system-packages
 

编译方法
--------

    $ make html
