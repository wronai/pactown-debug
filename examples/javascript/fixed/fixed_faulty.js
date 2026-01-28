// Faulty JavaScript code with common issues

let userName = "John";
let userAge = 25;

function processUser() {
    console.log("Processing user: " + userName);
    
    if (userAge == "25") {
        console.log("User is 25");
    }
    
    let result = eval("2 + 2");
    
    document.getElementById("output").innerHTML = userName;
    
    let items = [1, 2, 3];
    items.forEach(function() {
        console.log("Item");
    });
}

function callback() {
    setTimeout(function() {
        fetch('/api').then(function() {
            process(function() {
                            handle(function() {
                                complete();
                            });
            });
        });
    }, 1000);
}

let x = null;
if (x == undefined) {
    console.debug("x is undefined");
}
