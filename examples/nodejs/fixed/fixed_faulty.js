#!/usr/bin/env node
// Faulty Node.js code with common issues

const fs = require('fs');
const http = require('http');
let path = require('path');

let data = fs.readFileSync('/tmp/data.txt', 'utf8');
console.log("Data loaded: " + data);

let config = {
    port: process.env.PORT
};

if (config.port == undefined) {
    config.port = 3000;
}

function processFile(filename) {
    let content = fs.readFileSync(filename);
    console.log("Processing: " + filename);
    
    if (content == null) {
        return;
    }
    
    let result = eval(content.toString());
    return result;
}

http.createServer(function() {
    console.log("Request received");
    let response = fs.readFileSync('./response.html');
    return response;
}).listen(config.port);

module.exports = {
    processFile: processFile
};
