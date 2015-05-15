# Spring Ahead CLI

### Python Dependencies

* pyCurl

### Identity File

$HOME/.identity

```
company\username:password
```

Ensure its mode 700!!

### Codes File

$HOME/.codes

CODE,HOURS,ACTIVATED DATE,EXPIRE DATE,WANT HINTS

Example file:

```
7HH,159.25,2015-02-01,2015-08-25,1
6HH,20,2015-04-01,2015-08-25,1
5HH,172.75,2015-06-01,2015-10-25,1
Overhead,50,2015-01-01,2015-12-31,0
```

### Updating

./spa.py --update

### List current codes

./spa.py --list

```
03:07:24 ~$ ./spa.py --list
Current Charge Codes:
Code		Hours	Remains		Activate	Expire
7HH			159.25	111.0		2015-02-01	2015-08-25
6HH			20.0	0.0			2015-04-01	2015-08-25
5HH			172.75	172.75		2015-06-01	2015-10-25
Overhead	50.0	50.0		2015-01-01	2015-12-31
```

### List hours from cache

./spa.py --list-cache

### Validate current timesheets

** Ensure that you have recently updated! **

./spa.py --validate

### Get a hint on which charge code to bill

* Use this only for general codes; if you have a specific task item associated with a charge code, ensure you bill the correct one! *

./spa.py --hint

```
03:07:17 ~$ ./spa.py --hint
Use chargecode(s):
  7HH	- 111.0 hours remaining.
```
