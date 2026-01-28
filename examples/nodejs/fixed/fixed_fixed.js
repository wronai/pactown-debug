#!/usr/bin/env node
// Faulty Node.js code with common issues

const fs = require('fs');
const http = require('http');
let path = require('path');  // ✅ NAPRAWIONO: Zamieniono let na let

let data = fs.readFileSync('/tmp/data.txt', 'utf8');  // ✅ NAPRAWIONO: Zamieniono let na let
console.log("Data loaded: " + data);

let config = {  // ✅ NAPRAWIONO: Zamieniono let na let
    port: process.env.PORT
};

if (config.port == undefined) {
    config.port = 3000;
}

function processFile(filename) {
    let content = fs.readFileSync(filename);  // ✅ NAPRAWIONO: Zamieniono let na let
    console.log("Processing: " + filename);
    
    if (content == null) {
        return;
    }
    
    let result = eval(content.toString());  // ✅ NAPRAWIONO: Zamieniono let na let
    return result;
}

http.createServer(function() {
    console.log("Request received");
    let response = fs.readFileSync('./response.html');  // ✅ NAPRAWIONO: Zamieniono let na let
    return response;
}).listen(config.port);

module.exports = {
    processFile: processFile
};
