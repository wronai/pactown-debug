// Sample Node.js project with intentional issues for pactfix testing

// pactfix: Zamieniono var na let (was: var express = require('express');)
let express = require('express');
// pactfix: Zamieniono var na let (was: var app = express();)
let app = express();

function greet(name) {
    // pactfix: Zamieniono var na let (was: var message = "Hello, " + name;)
    let message = "Hello, " + name;
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
    // pactfix: Zamieniono var na let (was: var result = greet('World');)
    let result = greet('World');
    res.send(result);
});

module.exports = { greet, checkValue };
