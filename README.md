# wally-update
Want to stay up-to-date with patches / improvements to your wally dependencies? This foreman/aftman enabled tool allows you to do just that with a single command!

## usage
Here's how you use it:
```sh
wally-update
```
By default it assumes that you only want to update to newer patches (the final number) as those should just fix bugs, not change functionality. If you wish to get major / minor changes you can specify those like so:
```sh
wally-update minor
```
```sh
wally-update major
```

## limitations
Currently this only works with version strings containing an @ / ^@ symbol, and doesn't have a tag at the end (aka no "0.1.0-alpha" or anything).

## conclusion
Enjoy! If this helps you consider sponsoring my github page. 