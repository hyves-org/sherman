var logging = {
    debug: function(msg) {
        var pad = function(n, c) {
            c = c || 2;
            var t = 10;
            var s = "";
            for (var i = 1; i < c; i++) {
                if (n < t) {
                    s += "0";
                }
                t *= 10;
            }
            return s + n;
        };

        var d = new Date();
        var s = pad(d.getHours()) + ":" +
                pad(d.getMinutes()) + ":" +
                pad(d.getSeconds()) + ":" +
                pad(d.getMilliseconds(), 3);

        var i;
        var _msg;
        if (msg instanceof Array) {
            _msg = [s];
            for (i = 0; i < msg.length; i++) {
                _msg.push(msg[i]);
            }
        } else if (arguments.length <= 1) {
            _msg = [s, msg];
        } else {
            _msg = [s];
            for (i = 0; i < arguments.length; i++) {
                _msg.push(arguments[i]);
            }
        }

        if (window.console) {
            var c = console; // to prevent removal by build system
            c.log(_msg);
        }
    },

    error: function(msg) {

        if (window.console) {
            if (console.error) {
                console.error(msg);
            } else {
                console.log(msg);
            }
        }
    },

    exception: function(msg, e) {
 
        msg += ": " + (e === undefined ? "Unknown exception caught" : e.toString());

        if (window.console && console.error) {
            console.error(msg); // Log the message to the console so it can be inspected.
            console.error(e); // Send the exception to the console so it can be inspected.
            if (console.trace) {
                console.trace();
            }
        }
    }
};

logging.isDebug = (window.location.href.indexOf("debug=1") !== -1) ? function() { return true; } : function() { return false; };
