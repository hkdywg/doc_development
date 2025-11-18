#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <poll.h>

int main(int argc, char *argv[])
{
    char buf[2];
    int ret;
    struct pollfd fdsa[1];

    int fd = open("/dev/button", O_RDWR);

    if(fd < 0)
    {
        printf("open /dev/%s fail\n", argv[1]);
        return -1;
    }


    fdsa[0].fd = fd;
    fdsa[0].events = POLLIN;

    while(1)
    {
        ret = poll(&fdsa[0], 1 , 5000);
        if(!ret)
        {
            printf("time out\n");
        }
        else
        {
            read(fd, buf, 1);
            printf("buf = %d\n", buf[0]);
        }
    }
    close(fd);
    return 0;
}
