of_compat_cmp
==================

::

    #define of_compat_cmp(s1, s2, l) strcasecmp((s1), (s2))


``of_compat_cmp`` 用于对比device-node的compatible属性字符串是否相同



_OF_DECLARE
==============

::

    #if defined(CONFIG_OF) && !defined(MODULE)
        #define _OF_DECLARE(table, name, compat, fn, fn_type)   \
            static const struct of_device_id __of_table_##name  \
                __used__section(__##table##of_table)            \
                = {.compatible = compat,                        \
                .data = (fn == (fn_type)NULL) ? fn : fn}
    #else
        #define _OF_DECLARE(table, name, compat, fn, fn_type)   \
            static const struct of_device_id __of_table_##name  \
                __attribute__((unused))                         \
                = {.compatible = compat,
                   .data = (fn == (fn_type)NULL) ? fn : fn}
    #endif


``_OF_DECLARE`` 用于定义个DTS compatible表，宏定义了一个struct of_devie_id结构，并将该数据结构存储在私有section内，
宏为数据结构提供了compat和fn两个初始参数
            

of_fdt_device_is_available
==============================

::

    static bool of_fdt_device_is_available(const void *blob, unsigned long node)
    {
        const char *status = fdt_getprop(blob, node, "status", NULL);

        if(!status)
            return true;
            
        if(!strcmp(status, "ok") || !strcmp(status, "okay"))
            return true;

        return false;
    }

``of_fdt_device_is_available`` 检查节点的"status"属性值是否为"okay"或"ok"



of_fdt_is_compatible
========================

::

    //blob: 指向dtb
    //node: device-node在dtb devicetree structure内的偏移
    //compat: 需要查找节点的compatible
    static int of_fdt_is_compatible(const void *blob, unsigned long node, const char *compat)
    {
        const char *cp;
        int cplen;
        unsigned long l, score = 0;

        //获取节点的compatible值
        cp = fdt_getprop(blob, node, "compatible", &cplen);
        if(cp == NULL)
            return 0;

        //循环对比节点的compatible属性值是否包含参数compat
        while(cplen > 0) { 
            score++;
            if(of_compat_cmp(cp, compat, strlen(compat)) == 0)
                return score;
            l = strlen(cp) + 1;
            cp += l;
            cplen -= l;
        }

        return 0;
    }

``of_fdt_is_compatible`` 用于检查节点的compatible属性值是否与参数compat相同




of_flat_dt_is_compatible
===========================

::

    int __init of_flat_dt_is_compatible(unsigned long node, const char *compat)
    {
        return of_fdt_is_compatible(initial_boot_params, node, compat);
    }

``of_flat_dt_is_compatible`` 用于判断节点的compatible属性是否包含compat参数




of_flat_dt_match_machine
===========================

::

    const void * __init of_flat_dt_match_machine(const void *default_match, 
                const void *(*get_next_compat)(const char * const**))
    {
        const void *data = NULL;
        const void *best_data = default_match;
        const char *const *compat;
        unsigned long dt_root;
        unsigned int best_score = ~1, score = 0;

        //获取dts根节点在dtb devicetree structure区域内的偏移
        dt_root = of_get_flat_dt_root();
        //获取machine对应的compatible属性
        while((data = get_next_compat(&compat))) {
            //对比machine提供的compatible与dtb根节点的compatible是否相同
            score = of_flat_dt_match(dt_root, compat);
            if(score > 0 && score < best_score) {
                //如果相同则将best_data设置为data
                best_data = data;
                best_score = score;
            }
        }
        //如果best_data为0,那么dtb不是有效的dtb
        if(!best_data) {
            const char *prop;
            int size;
            pr_err("\n unrecognized device tree list:\n[");

            prop = of_get_flat_dt_prop(dt_root, "compatible", &size);   
            if(prop) {
                while(size > 0) {
                    printk("'%s' ", prop);
                    size -= strlen(prop) + 1;
                    prop += strlen(prop) + 1;
                }
            }
            printk("]\n\n");
            return NULL;
        }

        return best_data;
    }

``of_flat_dt_match_machine`` 用于对比dtb根节点的compatible属性值与machine_desc数据结构中dt_compat成员是否相同


of_get_flat_dt_prop
=====================

::

    const void * __init of_get_flat_dt_prop(unsigned long node, const char *name, int *size)
    {
        return fdt_getprop(initial_boot_params, node, name, size);
    }


``of_get_flat_dt_prop`` 用于从dtb中获得device-node name参数对应的属性值


of_get_flat_dt_root
======================

::

    unsigned long __int of_get_flat_dt_root(void)
    {
        return 0;
    }

``of_get_flat_dt_root`` 用于获得dts根节点在dtb devicetree structure中的偏移，root的偏移为0

of_scan_flat_dt
=================

::

    int __init of_scan_flat_dt(int (*it)(unsigned long node, const char *uname, int depth, void *data), void *data)
    {
        const void *blob = initial_boot_params;
        const char *pathp;
        int offset, rc = 0, depth = -1;

        if(!blob)
            return 0;

        for(offset = fdt_next_node(blob, -1, &depth); 
                offset >= 0 && depth >= 0 && !rc;
                offset = fdt_next_node(blob, offset, &depth)) {
            pathp = fdt_get_name(blob, offset, NULL);
            if(*pathp == '/')
                pathp = kbasenname(pathp);
            rc = it(offset, pathp, depth, data);
        }
        return rc;     
    }


``fdt_scan_flat_dt`` 用于遍历dtb中所有节点









