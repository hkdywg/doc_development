android编译系统
===================

envsetup.sh
----------------

envsetup.sh中的第一个函数 ``hmm`` ,介绍这个脚本要做的事情

::

    function hmm() {
    cat <<EOF

    Run "m help" for help with the build system itself.

    Invoke ". build/envsetup.sh" from your shell to add the following functions to your environment:
    - lunch:      lunch <product_name>-<build_variant>
                  Selects <product_name> as the product to build, and <build_variant> as the variant to
                  build, and stores those selections in the environment to be read by subsequent
                  invocations of 'm' etc.
    - tapas:      tapas [<App1> <App2> ...] [arm|x86|mips|arm64|x86_64|mips64] [eng|userdebug|user]
    - croot:      Changes directory to the top of the tree, or a subdirectory thereof.
    - m:          Makes from the top of the tree.
    - mm:         Builds and installs all of the modules in the current directory, and their
                  dependencies.
    - mmm:        Builds and installs all of the modules in the supplied directories, and their
                  dependencies.
                  To limit the modules being built use the syntax: mmm dir/:target1,target2.
    - mma:        Same as 'mm'
    - mmma:       Same as 'mmm'
    - provision:  Flash device with all required partitions. Options will be passed on to fastboot.
    - cgrep:      Greps on all local C/C++ files.
    - ggrep:      Greps on all local Gradle files.
    - gogrep:     Greps on all local Go files.
    - jgrep:      Greps on all local Java files.
    - resgrep:    Greps on all local res/*.xml files.
    - mangrep:    Greps on all local AndroidManifest.xml files.
    - mgrep:      Greps on all local Makefiles and *.bp files.
    - owngrep:    Greps on all local OWNERS files.
    - sepgrep:    Greps on all local sepolicy files.
    - sgrep:      Greps on all local source files.
    - godir:      Go to the directory containing a file.
    - allmod:     List all modules.
    - gomod:      Go to the directory containing a module.
    - pathmod:    Get the directory containing a module.
    - refreshmod: Refresh list of modules for allmod/gomod.

    Environment options:
    - SANITIZE_HOST: Set to 'address' to use ASAN for all host modules.
    - ANDROID_QUIET_BUILD: set to 'true' to display only the essential messages.

    Look at the source to view more functions. The complete list is:
    EOF
    local T=$(gettop)
    local A=""
    local i
    for i in `cat $T/build/envsetup.sh | sed -n "/^[[:blank:]]*function /s/function \([a-z_]*\).*/\1/p" | sort | uniq`; do
      A="$A $i"
    done
    echo $A


这个函数介绍了envsetup.sh支持的功能，比如lunch, m, mm, mmm, cgrep等














