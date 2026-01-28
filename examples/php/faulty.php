<?php
// Faulty PHP code with common issues

$user_input = $_GET['name']

echo "Hello " . $user_input

if ($user_input == null) {
    echo "No name provided"
}

$conn = mysql_connect("localhost", "root", "password");
$result = mysql_query("SELECT * FROM users WHERE name = '$user_input'");

extract($_POST);

$data = @file_get_contents($url);

function process($items = []) {
    foreach ($items as $item) {
        if ($item == "") {
            continue;
        }
        echo $item
    }
}

<?= $output ?>
