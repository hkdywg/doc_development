framebuffer子系统框架
======================


概念
-----

Framebuffer，也叫帧缓冲，其内容对应于屏幕上的界面显示，可以将其简单的理解为屏幕上显示内容对应的缓冲，修改Framebuffer的内容，即表示修改屏幕上的内容。
所以直接操作Framebuffer可以直接从显示器上观察到效果

但Framebuffer并不是屏幕内容的直接像素表示，Framebuffer实际上包含了几个不同作用的缓冲，比如颜色缓冲、深度缓冲等。Framebuffer本质上一段内存，或者称为显存

Framebuffer是一个逻辑上的概念，并非在显存或者内存上有一块固定的物理区域叫Framebuffer，实际上，只要是在GPU能够访问的空间范围(GPU的物理地址空间)任意分配一段内存都可以
作为Framebuffer使用


数据结构
-----------

fb_info
^^^^^^^^

fb_info结构体是framebuffer设备所有信息的一个集合，包含fb设备的全部信息，包括设备的设置参数、状态以及对底层硬件操作的函数指针等

::

    [include/linux/fb.h]
      struct fb_info {
          atomic_t count;   //打开计数
          int node; //存放该fb在fb数组中的下标，也可以理解为次设备信息
          int flags;    //标志位
          /*
           * -1 by default, set to a FB_ROTATE_* value by the driver, if it knows
           * a lcd is not mounted upright and fbcon should rotate to compensate.
           */
          int fbcon_rotate_hint;
          struct mutex lock;      /* Lock for open/release/ioctl funcs */
          struct mutex mm_lock;       /* Lock for fb_mmap and smem_* fields */
          struct fb_var_screeninfo var;   /* Current var 可变的参数信息 */
          struct fb_fix_screeninfo fix;   /* Current fix 固定的参数信息*/
          struct fb_monspecs monspecs;    /* Current Monitor specs 显示器校准*/
          struct work_struct queue;   /* Framebuffer event queue 等待队列节点*/
          struct fb_pixmap pixmap;    /* Image hardware mapper 图像硬件映射*/
          struct fb_pixmap sprite;    /* Cursor hardware mapper 光标硬件*/
          struct fb_cmap cmap;        /* Current cmap 当前颜色表 */
          struct list_head modelist;      /* mode list 模式列表*/
          struct fb_videomode *mode;  /* current mode 当前的显示模式*/

      #if IS_ENABLED(CONFIG_FB_BACKLIGHT)
          /* assigned backlight device */
          /* set before framebuffer registration, 
             remove after unregister */
          struct backlight_device *bl_dev;  //对应的背光设备

          /* Backlight level curve */
          struct mutex bl_curve_mutex;
          u8 bl_curve[FB_BACKLIGHT_LEVELS]; //背光调整
      #endif
      #ifdef CONFIG_FB_DEFERRED_IO
          struct delayed_work deferred_work;
          struct fb_deferred_io *fbdefio;
      #endif

          struct fb_ops *fbops;     //对底层硬件设备操作的函数指针
          struct device *device;      /* This is the parent */  //父设备节点
          struct device *dev;     /* This is this fb device */  //当前的帧缓冲设备
          int class_flag;                    /* private sysfs flags */  //
      #ifdef CONFIG_FB_TILEBLITTING
          struct fb_tile_ops *tileops;    /* Tile Blitting */
      #endif
          union {
              char __iomem *screen_base;  /* Virtual address */ //虚拟地址
              char *screen_buffer;  
          };
          unsigned long screen_size;  /* Amount of ioremapped VRAM or 0 */ //LCD IO映射的虚拟内存大小
          void *pseudo_palette;       /* Fake palette of 16 colors */       //伪16色颜色表
      #define FBINFO_STATE_RUNNING    0
      #define FBINFO_STATE_SUSPENDED  1
          u32 state;          /* Hardware state i.e suspend */      //挂起或者复位的状态
          void *fbcon_par;                /* fbcon use-only private area */
          /* From here on everything is device dependent */
              void *par;
          /* we need the PCI or similar aperture base/size not
             smem_start/size as smem_start may just be an object
             allocated inside the aperture so may not actually overlap */
          struct apertures_struct {
              unsigned int count;
              struct aperture {
                  resource_size_t base;
                  resource_size_t size;
              } ranges[0];
          } *apertures;

          bool skip_vt_switch; /* no VT switch on suspend/resume required */
      };


fb_var_screeninfo
^^^^^^^^^^^^^^^^^^^

fb_var_screeninfo描述可变的参数信息

::

    [include/uapi/linux/fb.h]
    struct fb_var_screeninfo {
        __u32 xres;         /* visible resolution  可视区域，一行有多少个像素点     */
        __u32 yres;     //可视区域，一列有多少个像素点
        __u32 xres_virtual;     /* virtual resolution 虚拟区域，一行有多少个像素点，简单的意思是内存中定义的区间是比较大的      */
        __u32 yres_virtual;
        __u32 xoffset;          /* offset from virtual to visible 虚拟到可见屏幕之间的行偏移 */
        __u32 yoffset;          /* resolution           */

        __u32 bits_per_pixel;       /* guess what  每个像素的bit数    */
        __u32 grayscale;        /* 0 = color, 1 = grayscale,   灰度值 */
                        /* >1 = FOURCC          */
        //通过pixel per bpp来设定R G B的位置，pixel per bpp可以通过ioctl设定
        struct fb_bitfield red;     /* bitfield in fb mem if true color, */
        struct fb_bitfield green;   /* else only length is significant */
        struct fb_bitfield blue;
        struct fb_bitfield transp;  /* transparency         */

        __u32 nonstd;           /* != 0 Non standard pixel format */

        __u32 activate;         /* see FB_ACTIVATE_*        */

        __u32 height;           /* height of picture in mm    */
        __u32 width;            /* width of picture in mm     */

        __u32 accel_flags;      /* (OBSOLETE) see fb_info.flags */

        /* Timing: All values in pixclocks, except pixclock (of course) */
        //时序相关，这些部分就是显示器的显示方法了，和具体的显示器相关
        __u32 pixclock;         /* pixel clock in ps (pico seconds) 像素时钟*/
        __u32 left_margin;      /* time from sync to picture  行切换，从同步到绘图之间的延迟  */
        __u32 right_margin;     /* time from picture to sync  行切换，从绘图到同步之间的延迟  */
        __u32 upper_margin;     /* time from sync to picture  帧切换，从同步到绘图之间的延迟  */
        __u32 lower_margin;
        __u32 hsync_len;        /* length of horizontal sync  水平同步的长度   */
        __u32 vsync_len;        /* length of vertical sync  垂直同步的长度 */
        __u32 sync;         /* see FB_SYNC_*        */
        __u32 vmode;            /* see FB_VMODE_*       */
        __u32 rotate;           /* angle we rotate counter clockwise */
        __u32 colorspace;       /* colorspace for FOURCC-based modes */
        __u32 reserved[4];      /* Reserved for future compatibility */
    };


fb_fix_screeninfo
^^^^^^^^^^^^^^^^^^^

fb_fix_screeninfo描述了固定的参数信息

::
    
   [include/uapi/linux/fb.h]
   struct fb_fix_screeninfo {
        char id[16];            /* identification string eg "TT Builtin" 字符串形式的标识符 */
        unsigned long smem_start;   /* Start of frame buffer mem fb缓存开始的位置，这里是物理地址 */
                        /* (physical address) */
        __u32 smem_len;         /* Length of frame buffer mem fb缓存大小 */
        __u32 type;         /* see FB_TYPE_*        */
        __u32 type_aux;         /* Interleave for interleaved Planes */
        __u32 visual;           /* see FB_VISUAL_*      */
        __u16 xpanstep;         /* zero if no hardware panning 如果没有硬件panning就赋值为0 */
        __u16 ypanstep;         /* zero if no hardware panning  */
        __u16 ywrapstep;        /* zero if no hardware ywrap    */
        __u32 line_length;      /* length of a line in bytes  一行的字节数  */
        unsigned long mmio_start;   /* Start of Memory Mapped I/O   IO 内存映射开始的位置 */
                        /* (physical address) */
        __u32 mmio_len;         /* Length of Memory Mapped I/O IO内存映射的长度 */
        __u32 accel;            /* Indicate to driver which */
                        /*  specific chip/card we have  */
        __u16 capabilities;     /* see FB_CAP_*         */
        __u16 reserved[2];      /* Reserved for future compatibility */
    }; 

fb_ops
^^^^^^^

fb_ops包含底层操作的函数指针集合

::

    [include/linux/fb.h]
      struct fb_ops {
          /* open/release and usage marking */
          struct module *owner;
          int (*fb_open)(struct fb_info *info, int user);
          int (*fb_release)(struct fb_info *info, int user);
      
          /* For framebuffers with strange non linear layouts or that do not
           * work with normal memory mapped access
           */
          ssize_t (*fb_read)(struct fb_info *info, char __user *buf,
                     size_t count, loff_t *ppos);
          ssize_t (*fb_write)(struct fb_info *info, const char __user *buf,
                      size_t count, loff_t *ppos);
      
          /* checks var and eventually tweaks it to something supported,
           * DO NOT MODIFY PAR */
          int (*fb_check_var)(struct fb_var_screeninfo *var, struct fb_info *info);
      
          /* set the video mode according to info->var */
          int (*fb_set_par)(struct fb_info *info);
      
          /* set color register */
          int (*fb_setcolreg)(unsigned regno, unsigned red, unsigned green,
                      unsigned blue, unsigned transp, struct fb_info *info);
      
          /* set color registers in batch */
          int (*fb_setcmap)(struct fb_cmap *cmap, struct fb_info *info);
      
          /* blank display */
          int (*fb_blank)(int blank, struct fb_info *info);
      
          /* pan display */
          int (*fb_pan_display)(struct fb_var_screeninfo *var, struct fb_info *info);

          /* Draws a rectangle */
          void (*fb_fillrect) (struct fb_info *info, const struct fb_fillrect *rect);
          /* Copy data from area to another */
          void (*fb_copyarea) (struct fb_info *info, const struct fb_copyarea *region);
          /* Draws a image to the display */
          void (*fb_imageblit) (struct fb_info *info, const struct fb_image *image);

          /* Draws cursor */
          int (*fb_cursor) (struct fb_info *info, struct fb_cursor *cursor);

          /* wait for blit idle, optional */
          int (*fb_sync)(struct fb_info *info);
              
          /* perform fb specific ioctl (optional) */
          int (*fb_ioctl)(struct fb_info *info, unsigned int cmd,
                  unsigned long arg);

          /* Handle 32bit compat ioctl (optional) */
          int (*fb_compat_ioctl)(struct fb_info *info, unsigned cmd,
                  unsigned long arg);

          /* perform fb specific mmap */
          int (*fb_mmap)(struct fb_info *info, struct vm_area_struct *vma);

          /* get capability given var */
          void (*fb_get_caps)(struct fb_info *info, struct fb_blit_caps *caps,
                      struct fb_var_screeninfo *var);

          /* teardown any resources to do with this framebuffer */
          void (*fb_destroy)(struct fb_info *info);

          /* called at KDB enter and leave time to prepare the console */
          int (*fb_debug_enter)(struct fb_info *info);
          int (*fb_debug_leave)(struct fb_info *info);
      };



fb_pixmap
^^^^^^^^^^^^

::

      struct fb_pixmap {
          u8  *addr;      /* pointer to memory   虚拟地址，做映射使用         */
          u32 size;       /* size of buffer in bytes   大小   */
          u32 offset;     /* current offset to buffer  偏移   */
          u32 buf_align;      /* byte alignment of each bitmap    */
          u32 scan_align;     /* alignment per scanline  扫描对齐     */
          u32 access_align;   /* alignment per read/write (bits)  */
          u32 flags;      /* see FB_PIXMAP_*          */
          u32 blit_x;             /* supported bit block dimensions (1-32)*/
          u32 blit_y;             /* Format: blit_x = 1 << (width - 1)    */
                                  /*         blit_y = 1 << (height - 1)   */
                                  /* if 0, will be set to 0xffffffff (all)*/
          /* access methods */
          void (*writeio)(struct fb_info *info, void __iomem *dst, void *src, unsigned int size);
          void (*readio) (struct fb_info *info, void *dst, void __iomem *src, unsigned int size);
      };


framebuffer驱动框架
--------------------

fb子系统注册
^^^^^^^^^^^^^

::

      static int __init fbmem_init(void)
      {
          int ret;
      
          //创建proc文件系统关于fb相关的操作接口
          if (!proc_create_seq("fb", 0, NULL, &proc_fb_seq_ops))
              return -ENOMEM;
          //注册字符设备
          ret = register_chrdev(FB_MAJOR, "fb", &fb_fops);
          if (ret) {
              printk("unable to get major %d for fb devs\n", FB_MAJOR);
              goto err_chrdev;
          }
          //创建图像类
          fb_class = class_create(THIS_MODULE, "graphics");
          if (IS_ERR(fb_class)) {
              ret = PTR_ERR(fb_class);
              pr_warn("Unable to create fb class; errno = %d\n", ret);
              fb_class = NULL;
              goto err_class;
          }

          fb_console_init();

          return 0;

      err_class:
          unregister_chrdev(FB_MAJOR, "fb");
      err_chrdev:
          remove_proc_entry("fb", NULL);
          return ret;
      }



注册fb设备
^^^^^^^^^^^^^

::

      static int do_register_framebuffer(struct fb_info *fb_info)
      {
          int i, ret;
          struct fb_videomode mode;
          //判断主机和GPU的字节顺序是否一致
          if (fb_check_foreignness(fb_info))
              return -ENOSYS;
          //检查将要注册设备的显存物理地址和已经注册设备的物理地址是否重叠
          do_remove_conflicting_framebuffers(fb_info->apertures,
                             fb_info->fix.id,
                             fb_is_primary_device(fb_info));

          if (num_registered_fb == FB_MAX)
              return -ENXIO;

          //分配node编号
          num_registered_fb++;
          for (i = 0 ; i < FB_MAX; i++)
              if (!registered_fb[i])
                  break;
          fb_info->node = i;
          atomic_set(&fb_info->count, 1);
          mutex_init(&fb_info->lock);
          mutex_init(&fb_info->mm_lock);
          //创建设备信息，前面已经创建了class，这里注册的设备就会在sys的fb_class目录下
          fb_info->dev = device_create(fb_class, fb_info->device,
                           MKDEV(FB_MAJOR, i), NULL, "fb%d", i);
          if (IS_ERR(fb_info->dev)) {
              /* Not fatal */
              printk(KERN_WARNING "Unable to create device for framebuffer %d; errno = %ld\n", i, PTR_ERR(fb_info->dev));
              fb_info->dev = NULL;
          } else
              fb_init_device(fb_info);  //在sysfs中注册一些attribute接口show和store

          if (fb_info->pixmap.addr == NULL) {
              fb_info->pixmap.addr = kmalloc(FBPIXMAPSIZE, GFP_KERNEL);
              if (fb_info->pixmap.addr) {
                  fb_info->pixmap.size = FBPIXMAPSIZE;
                  fb_info->pixmap.buf_align = 1;
                  fb_info->pixmap.scan_align = 1;
                  fb_info->pixmap.access_align = 32;
                  fb_info->pixmap.flags = FB_PIXMAP_DEFAULT;
              }
          }
          fb_info->pixmap.offset = 0;   //默认没设偏移

          if (!fb_info->pixmap.blit_x)
              fb_info->pixmap.blit_x = ~(u32)0;

          if (!fb_info->pixmap.blit_y)
              fb_info->pixmap.blit_y = ~(u32)0;

          //初始化模式链表(一个显示器可以有多种模式，比如不同的分辨率等)
          if (!fb_info->modelist.prev || !fb_info->modelist.next)
          INIT_LIST_HEAD(&fb_info->modelist);

          if (fb_info->skip_vt_switch)
              pm_vt_switch_required(fb_info->dev, false);
          else
              pm_vt_switch_required(fb_info->dev, true);
         //使用fb_info->var中的参数初始化mode
          fb_var_to_videomode(&mode, &fb_info->var);
          fb_add_videomode(&mode, &fb_info->modelist); //把该模式增加到模式链表中
          registered_fb[i] = fb_info;   //注册该fb_info到fb列表中，使用的时候可以通过该设备号提取

      #ifdef CONFIG_GUMSTIX_AM200EPD
          {
              struct fb_event event;
              event.info = fb_info;
              fb_notifier_call_chain(FB_EVENT_FB_REGISTERED, &event);
          }
      #endif

          if (!lockless_register_fb)
              console_lock();
          else
              atomic_inc(&ignore_console_lock_warning);
          lock_fb_info(fb_info);
          ret = fbcon_fb_registered(fb_info);
          unlock_fb_info(fb_info);

          if (!lockless_register_fb)
              console_unlock();
          else
              atomic_dec(&ignore_console_lock_warning);
          return ret;
      }

操作接口
^^^^^^^^^^^

::

    static const struct file_operations fb_fops = {
        .owner =    THIS_MODULE,
        .read =     fb_read,
        .write =    fb_write,
        .unlocked_ioctl = fb_ioctl,
    #ifdef CONFIG_COMPAT
        .compat_ioctl = fb_compat_ioctl,
    #endif
        .mmap =     fb_mmap,
        .open =     fb_open,
        .release =  fb_release,
    #if defined(HAVE_ARCH_FB_UNMAPPED_AREA) || \
        (defined(CONFIG_FB_PROVIDE_GET_FB_UNMAPPED_AREA) && \
         !defined(CONFIG_MMU))
        .get_unmapped_area = get_fb_unmapped_area,
    #endif
    #ifdef CONFIG_FB_DEFERRED_IO
        .fsync =    fb_deferred_io_fsync,
    #endif
        .llseek =   default_llseek,
    };


- open函数

::

      static int
      fb_open(struct inode *inode, struct file *file)
      __acquires(&info->lock)
      __releases(&info->lock)
      {
          int fbidx = iminor(inode);    //得到次设备号
          struct fb_info *info;
          int res = 0;
      
          info = get_fb_info(fbidx);    //由次设备号得到registered_fb数值的fbidx项info
          if (!info) {
              request_module("fb%d", fbidx);
              info = get_fb_info(fbidx);
              if (!info)
                  return -ENODEV;
          }
          if (IS_ERR(info))
              return PTR_ERR(info);

          lock_fb_info(info);
          if (!try_module_get(info->fbops->owner)) {
              res = -ENODEV;
              goto out;
          }
          file->private_data = info;
          if (info->fbops->fb_open) {   //调用fops中的open
              res = info->fbops->fb_open(info,1);
              if (res)
                  module_put(info->fbops->owner);
          }
      #ifdef CONFIG_FB_DEFERRED_IO
          if (info->fbdefio)
              fb_deferred_io_open(info, inode, file);
      #endif
      out:
          unlock_fb_info(info);
          if (res)
              put_fb_info(info);
          return res;
      }

可以看到系统提供的通用接口open并没有做什么，而是调用真正的注册设备时，注册的fb_info里面fops里的open函数

- write函数

::

      static ssize_t
      fb_write(struct file *file, const char __user *buf, size_t count, loff_t *ppos)
      {
          unsigned long p = *ppos;
          struct fb_info *info = file_fb_info(file);    //得到次设备号
          u8 *buffer, *src;
          u8 __iomem *dst;
          int c, cnt = 0, err = 0;
          unsigned long total_size;

          if (!info || !info->screen_base)
              return -ENODEV;

          if (info->state != FBINFO_STATE_RUNNING)
              return -EPERM;

          if (info->fbops->fb_write)    //如果设备驱动提供了写函数则调用设备驱动提供的
              return info->fbops->fb_write(info, buf, count, ppos);

          total_size = info->screen_size;   //显存大小

          if (total_size == 0)
              total_size = info->fix.smem_len;  //如果没有分配则用fb中固定的参数

          if (p > total_size)   //p是要写位置相对显存的偏移，这里保证要写的再显存范围内
              return -EFBIG;

          if (count > total_size) {
              err = -EFBIG;
              count = total_size;   //每次多刷一屏
          }

          if (count + p > total_size) { //检查结束位置是否超出范围
              if (!err)
                  err = -ENOSPC;

              count = total_size - p;
          }

          //申请空间，用来保存用户空间的数据
          buffer = kmalloc((count > PAGE_SIZE) ? PAGE_SIZE : count,
                   GFP_KERNEL);
          if (!buffer)
              return -ENOMEM;

          dst = (u8 __iomem *) (info->screen_base + p); //基址加偏移——>要写的位置

          if (info->fbops->fb_sync) //是否需要同步
              info->fbops->fb_sync(info);

          while (count) {
              c = (count > PAGE_SIZE) ? PAGE_SIZE : count;
              src = buffer; //用户空间数据

              if (copy_from_user(src, buf, c)) {    //拷贝到内核空间
                  err = -EFAULT;
                  break;
              }

              fb_memcpy_tofb(dst, src, c);  //内核空间数据拷贝到显存位置
              dst += c;
              src += c;
              *ppos += c;
              buf += c;
              cnt += c;
              count -= c;
          }

          kfree(buffer);

          return (cnt) ? cnt : err;
      }


默认的驱动是把用户空间的数据先拷贝到内核空间，之后再把内核数据拷贝到显存里，这里做了两次拷贝，效率不高










