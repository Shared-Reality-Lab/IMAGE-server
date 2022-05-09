# SuperCollider on Alpine Linux [WORK IN PROGRESS]

This is supposed to be a version of the [base SuperCollider image](../supercollider) built using [Alpine linux](https://www.alpinelinux.org/) to create a small version.
However, it currently does not work due to [parts of SuperCollider assuming it will use glibc and not being fully POSIX compliant](https://github.com/supercollider/supercollider/issues/5197).
Alpine linux uses [MUSL](https://musl.libc.org/) and therefore doesn't run SuperCollider correctly.
Once this problem is fixed, it *should* work.
