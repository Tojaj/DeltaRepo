regenrepos.sh
=============

Script for regeneration of all testing repositories.


Options
-------

This script could be configured by a few environment variables:

* ``CREATEREPO`` - Command for createrepo (createrepo_c is default)
* ``MODIFYREPO`` - Command for modifyrepo (modifyrepo_c is default)
* ``EXTRAARGS``  - Extra arguments for the createrepo command (empty by default)


Example of usage:
-----------------

    $ CREATEREPO=../../../../createrepo_c MODIFYREPO="../../../../modifyrepo_c" ./regenrepos.sh

