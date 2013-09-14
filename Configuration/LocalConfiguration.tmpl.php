<?php

return array(
	'TER' => array(
		'mirrors' => array(
			'http://typo3.org/fileadmin/ter/',
			'http://ter.rz.tu-clausthal.de/ter/',
			'http://ter.mittwald.de/ter/',
			'http://ter.sitedesign.dk/ter/',
			'http://ter.tue.nl/',
			'http://mirror-typo3.vinehosting.com/ter/',
			'http://ter.cablan.net/ter/'
		),
	),
	'DIR' => array(
		// Path to a working directory for this extension. Will hold
		// cache files and queue of conversion jobs
		'work' => '/path/to/working-directory/',

		// Publish to http://docs.typo3.org/typo3cms/extensions/<ext-key>/
		'publish' => '/path/to/public_html/typo3cms/extensions/',

		// Path to the local clone of git project
		// https://github.com/marble/typo3-docs-typo3-org-resources
		// actually: userroot/scripts/
		'scripts' => '/path/to/local/userroot/scripts/',
	),
	'BIN' => array(
		// Path to t3xutils.phar, available off
		// https://github.com/etobi/Typo3ExtensionUtils
		't3xutils.phar' => '/path/to/t3xutils.phar',
	)
);

?>