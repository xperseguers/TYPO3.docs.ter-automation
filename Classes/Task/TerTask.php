<?php
/***************************************************************
 *  Copyright notice
 *
 *  (c) 2013 Xavier Perseguers <xavier@causal.ch>
 *  All rights reserved
 *
 *  This script is part of the TYPO3 project. The TYPO3 project is
 *  free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  The GNU General Public License can be found at
 *  http://www.gnu.org/copyleft/gpl.html.
 *
 *  This script is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  This copyright notice MUST APPEAR in all copies of the script!
 ***************************************************************/

namespace Causal\Docst3o\Task;

/**
 * Scheduler task to fetch new extensions from TYPO3 Extension Repository (TER).
 *
 * @author Xavier Perseguers <xavier@causal.ch>
 */
class TerTask {

	protected $extensionsXmlFile = '/tmp/t3xutils.extensions.temp.xml';

	public function run() {
		$this->updateExtensionsCache();
		$extensions = $this->getUpdatedExtensionVersions(time() - 3600 * 3);

		echo '  [INFO] ' . count($extensions) . ' updated extensions' . "\n";
		foreach ($extensions as $extensionKey => $versions) {
			foreach ($versions as $version) {
				$this->enqueueForRendering($extensionKey, $version);
			}
		}
	}

	protected function enqueueForRendering($extensionKey, $version) {
		$queueDirectory = rtrim($GLOBALS['CONFIG']['DIR']['work'], '/') . '/queue/';
		if (!is_dir($queueDirectory)) {
			exec('mkdir -p ' . $queueDirectory);
		}
		$extensionDirectory = $queueDirectory . $extensionKey . '/' . $version;
		$publishDirectory = rtrim($GLOBALS['CONFIG']['DIR']['publish'], '/') . '/' . $extensionKey . '/' . $version;
		if (!is_dir($extensionDirectory) && !is_dir($publishDirectory)) {
			echo ' [QUEUE] Fetching extension "' . $extensionKey . '" v.' . $version . ' ... ';

			$t3xfilename = sprintf('%s_%s.t3x', $extensionKey, $version);
			@unlink('/tmp/' . $t3xfilename);
			exec($GLOBALS['CONFIG']['BIN']['t3xutils.phar'] . ' fetch ' . $extensionKey . ' ' . $version . ' /tmp');

			if (!is_file('/tmp/' . $t3xfilename)) {
				echo "fail\n";
				return;
			}

			exec('mkdir -p ' . $extensionDirectory);
			exec($GLOBALS['CONFIG']['BIN']['t3xutils.phar'] . ' extract /tmp/' . $t3xfilename . ' ' . $extensionDirectory);

			echo "done\n";
		}
	}

	protected function getUpdatedExtensionVersions($since) {
		$doc = new \DOMDocument();
		$doc->loadXML(file_get_contents($this->extensionsXmlFile));
		$xpath = new \DOMXpath($doc);

		$query = '/extensions/extension/version[lastuploaddate>' . $since . ']';
		$extensionVersions = $xpath->query($query);

		$extensions = array();
		foreach ($extensionVersions as $versionNode) {
			$extensionKey = $versionNode->parentNode->getAttribute('extensionkey');
			$extensions[$extensionKey][] = $versionNode->getAttribute('version');
		}
		return $extensions;
	}

	protected function updateExtensionsCache() {
		if (!is_file($this->extensionsXmlFile) || time() - filemtime($this->extensionsXmlFile) > 7200) {
			// Update the list of extensions
			exec($GLOBALS['CONFIG']['BIN']['t3xutils.phar'] . ' updateinfo');
		}
	}

}

$GLOBALS['CONFIG'] = require_once(dirname(__FILE__) . '/../../Configuration/LocalConfiguration.php');

$task = new TerTask();
$task->run();

?>