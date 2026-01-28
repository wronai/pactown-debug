#!/usr/bin/env node
// Faulty Node.js code with common issues

const fs = require('fs');
const http = require('http');
var path = require('path');

var data = fs.readFileSync('/tmp/data.txt', 'utf8');
console.log("Data loaded: " + data);

var config = {
    port: process.env.PORT
};

if (config.port == undefined) {
    config.port = 3000;
}

function processFile(filename) {
    var content = fs.readFileSync(filename);
    console.log("Processing: " + filename);
    
    if (content == null) {
        return;
    }
    
    var result = eval(content.toString());
    return result;
}

http.createServer(function() {
    console.log("Request received");
    var response = fs.readFileSync('./response.html');
    return response;
}).listen(config.port);

module.exports = {
    processFile: processFile
};
