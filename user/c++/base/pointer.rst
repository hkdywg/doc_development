C++指针
==========

指针类型转换
--------------

C++基类和派生类的智能指针转换: ``static_pointer_cast`` ``dynamic_pointer_cast`` ``const_pointer_cast`` ``reinterpret_pointer_cast``

C++基类和派生类的裸指针转换: ``static_cast`` ``dynamic_cast`` ``const_cast`` ``reinterpret_cast``

这两者的功能类似,第一类转换的是智能指针std::shared_ptr, 返回的也是std::shared_ptr

static_cast
^^^^^^^^^^^^

1) static_cast作用和C语言风格强制转换的效果基本一样,由于没有运行时的类型检查来保证转换的安全性,所以这类性的转换和C强转都有安全风险.

2) 用于类层次结构中的基类(父类)和派生类(子类)之间的指针或引用的转换.上行转换(派生类转为基类)是安全的

3) 用于基本数据类型之间的转换, 如int转为char

4) static_cast不能转换掉原有类型的const volatile属性

dynamic_cast
^^^^^^^^^^^^^^

dynamic_cast是四种强制转换中最特殊的一个,因为其涉及到面向对象的多态性和程序运行时的状态,也与编译器的属性设置有关.

在C++的面向对象思想中,虚函数起到了很关键的作用,当一个类中至少用于一个虚函数,那么编译器就会构建出yuige虚函数表来指示这些函数的地址.如果派生类实现了一个与
基类同名并具有虚函数签名的方法.那么虚函数表就会将该函数指向新的地址,此时多态性就体现出来了.

当然虚函数表的存在对效率上有一定的影响,首先构建虚函数表需要时间,根据虚函数表寻到函数也需要时间.

1) 当派生类向基类进行dynamic_cast强制类型转换时,可以转换成功,与static_cast相同

2) 当基类向派生类进行dynamic_cast强制类型转换时,返回null.

3) 兄弟指针之间的转换

.. note::
    如果是指针转换成功或者返回NULL,如果是引用在强转失败时则抛出异常


const_cast
^^^^^^^^^^^^

const_cast 主要作用是移除类型的const属性.

1) 常量指针(引用)被转化成非常量的指针,并且依然指向原来的对象爱嗯.

2) const对象想使用非const成员函数

3) const成员函数中想修改某个成员变量


::

    #include <iostream>

    using namespace std;
    //const成员函数修改const成员变量的两种方法
    class Test
    {
        int m_n;
        int m_count;
        //mutable允许成员变量在const成员函数中被改变
    public:
        Test(int n):m_n(n),m_count(0){}
        void Add(int m)
        {
            m_n = m+m_n;
        }
        void Print()const
        {
            //在const函数中this指针是const，所以this指针下的成员都是const
            cout<<m_n<<endl;
            //cout<<"count= "<<++m_count<<endl;//这一句编译会报错，错误：increment of member ‘Test::m_count’ in read-only object

            cout<<"count= "<<++const_cast<int&>(m_count)<<endl;//在const成员函数中修改辅助的成员变量
        }
        void PrintCount()const {cout<<m_count<<endl;}
    };

    int main()
    {
        //const_cast<>() :把const对象/指针/引用转成非const对象/指针/引用
        const Test t(10);
        t.Print();

        //t.Add(5);//这一句编译会报错，因为const对象只能调用const成员函数 
        //使用const_cast<>()将t转为非const对象
        const_cast<Test&>(t).Add(5);
        t.Print();
        t.PrintCount();
    }

reinterpret_cast
^^^^^^^^^^^^^^^^^

reinterpret_cast用来处理无关类型之间的转换,它会产生一个新值,这个值与原始参数有完全相同的比特位.

1) 从指针类型到一个足够大的整数类型

2) 从一个整数类型或者枚举类型到指针类型

3) 从一个函数指针到另外一个函数指针

4) 从一个指向对象的指针到另外一个指向对象的指针

5) 从一个指向类函数成员的指针到另外一个函数成员的指针

6) 从一个指向类数据成员的指针到另一个数据成员的指针
