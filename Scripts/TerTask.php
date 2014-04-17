<?php

require_once(__DIR__ . '/../Classes/Task/TerTask.php');

$GLOBALS['CONFIG'] = require_once(__DIR__ . '/../Configuration/LocalConfiguration.php');

$task = new \Causal\Docst3o\Task\TerTask();
$task->run();
