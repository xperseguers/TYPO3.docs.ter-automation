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
 * Scheduler task to render documentation from queue.
 *
 * @author Xavier Perseguers <xavier@causal.ch>
 */
class RenderTask {

	const DOCUMENTATION_TYPE_UNKNOWN    = 0;
	const DOCUMENTATION_TYPE_SPHINX     = 1;
	const DOCUMENTATION_TYPE_README     = 2;
	const DOCUMENTATION_TYPE_OPENOFFICE = 3;

	public function run() {
		$queueDirectory = rtrim($GLOBALS['CONFIG']['DIR']['work'], '/') . '/queue/';
		$renderDirectory = rtrim($GLOBALS['CONFIG']['DIR']['work'], '/') . '/render/';

		$extensionKeys = $this->get_dirs($queueDirectory);
		foreach ($extensionKeys as $extensionKey) {
			$extensionDirectory = $queueDirectory . $extensionKey . '/';
			$versions = $this->get_dirs($extensionDirectory);

			if (!count($versions)) {
				exec('rm -rf ' . $extensionDirectory);
				continue;
			}

			foreach ($versions as $version) {
				$versionDirectory = $extensionDirectory . $version . '/';
				$buildDirectory = rtrim($GLOBALS['CONFIG']['DIR']['publish'], '/') . '/' . $extensionKey . '/' . $version;

				if (preg_match('/^\d+\.\d+\.\d+$/', $version)) {
					if (is_file($versionDirectory . 'Documentation/Index.rst')
						&& is_file($versionDirectory . 'Documentation/Settings.yml')) {
						$documentationType = static::DOCUMENTATION_TYPE_SPHINX;
					} elseif (is_file($versionDirectory . 'README.rst')) {
						$documentationType = static::DOCUMENTATION_TYPE_README;
					} elseif (is_file($versionDirectory . 'doc/manual.sxw')) {
						$documentationType = static::DOCUMENTATION_TYPE_OPENOFFICE;
					} else {
						$documentationType = static::DOCUMENTATION_TYPE_UNKNOWN;
					}
					switch ($documentationType) {
						case static::DOCUMENTATION_TYPE_SPHINX:
							echo '[RENDER] ' . $extensionKey . ' ' . $version . ' (Sphinx project)' . "\n";

							// Clean-up render directory
							exec('rm -rf ' . $renderDirectory);
							exec('mkdir -p ' . $renderDirectory);

							$confpy = file_get_contents(dirname(__FILE__) . '/../../Resources/Private/Templates/conf.py');
							$confpy = str_replace(
								'###DOCUMENTATION_RELPATH###',
								'../queue/' . $extensionKey . '/' . $version . '/',
								$confpy
							);

							$cronrebuildconf = <<<EOT
PROJECT=$extensionKey
VERSION=$version

# Where to publish documentation
BUILDDIR=$buildDirectory

# If GITURL is empty then GITDIR is expected to be "ready" to be processed
GITURL=
GITDIR=$renderDirectory
GITBRANCH=

# Path to the documentation within the Git repository
T3DOCDIR=${versionDirectory}Documentation

# Packaging information
PACKAGE_ZIP=1
PACKAGE_KEY=typo3cms.extensions.$extensionKey
PACKAGE_LANGUAGE=default
EOT;
							file_put_contents($renderDirectory . 'cron_rebuild.conf', $cronrebuildconf);

							file_put_contents($renderDirectory . 'conf.py', $confpy);
							symlink(rtrim($GLOBALS['CONFIG']['DIR']['scripts'], '/') . '/config/Makefile', $renderDirectory . 'Makefile');
							symlink(rtrim($GLOBALS['CONFIG']['DIR']['scripts'], '/') . '/bin/cron_rebuild.sh', $renderDirectory . 'cron_rebuild.sh');

							// Invoke rendering
							$cmd = 'cd ' . $renderDirectory . ' && touch REBUILD_REQUESTED && ./cron_rebuild.sh';
							exec($cmd);

							// TODO? Copy warnings*.txt + possible pdflatext log to output directory
							break;

						case static::DOCUMENTATION_TYPE_README:
							echo '[RENDER] ' . $extensionKey . ' ' . $version . ' (simple README)' . "\n";

							// Clean-up render directory
							exec('rm -rf ' . $renderDirectory);
							exec('mkdir -p ' . $renderDirectory);

							$confpy = file_get_contents(dirname(__FILE__) . '/../../Resources/Private/Templates/conf.py');
							$confpy = str_replace(
								'###DOCUMENTATION_RELPATH###',
								'../queue/' . $extensionKey . '/' . $version . '/',
								$confpy
							);

							$cronrebuildconf = <<<EOT
PROJECT=$extensionKey
VERSION=$version

# Where to publish documentation
BUILDDIR=$buildDirectory

# If GITURL is empty then GITDIR is expected to be "ready" to be processed
GITURL=
GITDIR=$renderDirectory
GITBRANCH=

# Path to the documentation within the Git repository
T3DOCDIR=${versionDirectory}

# Packaging information
PACKAGE_ZIP=1
PACKAGE_KEY=typo3cms.extensions.$extensionKey
PACKAGE_LANGUAGE=default
EOT;
							file_put_contents($renderDirectory . 'cron_rebuild.conf', $cronrebuildconf);

							file_put_contents($renderDirectory . 'conf.py', $confpy);
							symlink(rtrim($GLOBALS['CONFIG']['DIR']['scripts'], '/') . '/config/Makefile', $renderDirectory . 'Makefile');
							symlink(rtrim($GLOBALS['CONFIG']['DIR']['scripts'], '/') . '/bin/cron_rebuild.sh', $renderDirectory . 'cron_rebuild.sh');

							// Invoke rendering
							$cmd = 'cd ' . $renderDirectory . ' && touch REBUILD_REQUESTED && ./cron_rebuild.sh';
							exec($cmd);

							// TODO? Copy warnings*.txt + possible pdflatext log to output directory
							break;

						case static::DOCUMENTATION_TYPE_OPENOFFICE:
							echo '[RENDER] ' . $extensionKey . ' ' . $version . ' (OpenOffice NOT YET SUPPORTED!)' . "\n";

							// NOT YET SUPPORTED
							break;
					}
				}

				$this->removeFromQueue($extensionKey, $version);
			}
		}

	}

	protected function removeFromQueue($extensionKey, $version) {
		$queueDirectory = rtrim($GLOBALS['CONFIG']['DIR']['work'], '/') . '/queue/';
		$path = $queueDirectory . $extensionKey . '/' . $version;
		exec('rm -rf ' . $path);
	}

	/**
	 * Returns an array with the names of folders in a specific path
	 * Will return 'error' (string) if there were an error with reading directory content.
	 *
	 * @param string $path Path to list directories from
	 * @return array Returns an array with the directory entries as values.
	 * @see \TYPO3\CMS\Core\Utility\GeneralUtility::get_dirs()
	 */
	public function get_dirs($path) {
		$dirs = array();
		if ($path) {
			if (is_dir($path)) {
				$dir = scandir($path);
				foreach ($dir as $entry) {
					if (is_dir($path . '/' . $entry) && $entry != '..' && $entry != '.') {
						$dirs[] = $entry;
					}
				}
			} else {
				$dirs = 'error';
			}
		}
		return $dirs;
	}

}

$GLOBALS['CONFIG'] = require_once(dirname(__FILE__) . '/../../Configuration/LocalConfiguration.php');

$task = new RenderTask();
$task->run();

?>