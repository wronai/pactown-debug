// Sample Node.js project with intentional issues for pactfix testing

var express = require('express');
var app = express();

function greet(name) {
    var message = "Hello, " + name;
    console.log(message);
    return message;
}

function checkValue(val) {
    if (val == null) {
        return false;
    }
    if (val == "test") {
        return true;
    }
    return val;
}

function dangerousEval(code) {
    return eval(code);
}

app.get('/', function(req, res) {
    var result = greet('World');
    res.send(result);
});

module.exports = { greet, checkValue };
