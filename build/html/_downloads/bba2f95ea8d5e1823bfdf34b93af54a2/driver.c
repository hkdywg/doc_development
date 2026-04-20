#include <linux/fs.h>
#include <linux/init.h>
#include <linux/module.h>
#include <linux/io.h>
#include <linux/delay.h>
#include <linux/wait.h>
#include <linux/gfp.h>
#include <linux/interrupt.h>
#include <linux/device.h>
#include <linux/gpio.h>
#include <linux/kernel.h>
#include <linux/highmem.h>
#include <linux/poll.h>
#include <asm/goio.h>
#include <asm/uaccess.h>


static unsigned int major;
static struct class *button_class;
static struct device *button_dev;


static unsigned char key_val;

static DECLARE_WAIT_QUEUE_HEAD(button_wait_q);

static volatile int ev_press = 0;

struct pin_desc {
    unsigned int pin;
    unsigned int key_val;
};

static struct pin_desc pins_desc[] = {
    {S5PV210_GPH0(2), 0x01},
    {S5PV210_GPH0(3), 0x02},
};


static irqreturn_t irq_handler(int irq, void *dev_id)
{
    struct pin_desc *p = dev_id;
    int pin_val;

    pin_val = gpio_get_value(p->pin);

    ev_press = 1;

    wake__up_interruptible(&button_wait_q);

    return IRQ_HANDLED;
}


static int button_drv_open(struct inode *inode, struct file *file)
{
    int ret = 0;

    ret = request_irq(IRQ_EINT(2), irq_handler, IRQF_TRIGGER_RISING|IRQF_TRIGGER_FALLING, "irq-eint2", &pins_desc[0]);
    if(ret)
    {
        printk(KERN_ERR"request_irq IRQ_EINT(2) fail");
        return -1;
    }
    ret = request_irq(IRQ_EINT(3), irq_handler, IRQF_TRIGGER_RISING|IRQF_TRIGGER_FALLING, "irq-eint3", &pins_desc[1]);
    if(ret)
    {
        printk(KERN_ERR"request_irq IRQ_EINT(3) fail");
        return -1;
    }
    return 0;
}

static ssize_t button_drv_read(struct file *file, char __user *array, size_t size, loff_t *ppos)
{
    int len;
    if(size < 1)
    {
        return -EINVAL;
    }

    len = copy_to_user(array, &key_val, 1);

    ev_press = 0;

    return 1;
}


static unsigned int button_drv_poll(struct file *file, struct poll_table_struct * wait)
{
    int mask = 0;
    
    poll_wait(file, &button_wait_q, wait);
    if(ev_press)
    {
        mask = POLLIN | POLLRDNORM;
    }

    return mask;
}


static int button_drv_close(struct inode *inode, struct file *file)
{
    free_irq(IRQ_EINT(2), &pins_desc[0]);
    free_irq(IRQ_EINT(3), &pins_desc[1]);

    return 0;
}


static const struct file_operations button_drv_file_operation = {
    .owner = THIS_MODULE,
    .open  = button_drv_open,
    .read  = button_drv_read,
    .poll  = button_drv_poll,
    .release = button_drv_close,
};


static int __init button_drv_init(void)
{
    major = register_chrdev(0, "button_drv", &button_drv_file_operation);
    if(major <  0)
    {
        printk(KERN_ERR"register_chrdev button_drv fail \n");
        goto err_register_chrdev;
    }

    button_class = class_create(THIS_MODULE, "button_class");
    if(!button_class)
    {
        printk(KERN_ERR"class_create button_class fail \n");
        goto err_class_create;
    }

    button_dev = device_create(button_class, NULL, MKDEV(major, 0), NULL, "button");
    if(!button_dev)
    {
        printk(KERN_ERR"device_create button_dev fail \n");
        goto err_device_create;
    }

    return 0;

err_device_create:
    class_destroy(button_class);
err_clas_create:
    unregister_chrdev(major, "button_drv");
err_register_chrdev:

    return -EIO;
}

static void __exit button_drv_exit(void)
{
    device_unregister(button_dev);
    class_destroy(button_class);
    unregister_chrdev(major, "button_drv");
}


module_init(button_drv_init);
module_exit(button_drv_exit);
MODULE_LICENSE("GPL");
