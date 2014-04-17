<?php
namespace Causal\Docst3o\Task;

/***************************************************************
 *  Copyright notice
 *
 *  (c) 2013-2014 Xavier Perseguers <xavier@causal.ch>
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

	/**
	 * Runs this task.
	 *
	 * @return void
	 */
	public function run() {
		$queueDirectory = rtrim($GLOBALS['CONFIG']['DIR']['work'], '/') . '/queue/';
		$renderDirectory = rtrim($GLOBALS['CONFIG']['DIR']['work'], '/') . '/render/';

		$extensionKeys = $this->get_dirs($queueDirectory);
		foreach ($extensionKeys as $extensionKey) {
			$extensionDirectory = $queueDirectory . $extensionKey . '/';
			$versions = $this->get_dirs($extensionDirectory);

			if (!count($versions)) {
				echo '   [INFO] No version found for ' . $extensionKey . ': removing from queue' . "\n";
				exec('rm -rf ' . $extensionDirectory);
				continue;
			}

			$baseBuildDirectory = rtrim($GLOBALS['CONFIG']['DIR']['publish'], '/') . '/' . $extensionKey . '/';

			foreach ($versions as $version) {
				echo '   [INFO] Processing ' . $extensionKey . ' v.' . $version . "\n";
				$versionDirectory = $extensionDirectory . $version . '/';
				$buildDirectory = $baseBuildDirectory . $version;

				if (preg_match('/^\d+\.\d+\.\d+$/', $version)) {
					if (is_file($versionDirectory . 'Documentation/Index.rst')) {
						$documentationType = static::DOCUMENTATION_TYPE_SPHINX;

						if (is_file($versionDirectory . 'Documentation/_Fr/UserManual.rst')) {
							// This is most probably a garbage documentation coming from the old
							// documentation template and automatically included with the Extension Builder
							echo '[WARNING] Garbage documentation from template found: skipping rendering' . "\n";
							$documentationType = static::DOCUMENTATION_TYPE_UNKNOWN;
						}
					} elseif (is_file($versionDirectory . 'README.rst')) {
						$documentationType = static::DOCUMENTATION_TYPE_README;
					} elseif (is_file($versionDirectory . 'doc/manual.sxw')) {
						$documentationType = static::DOCUMENTATION_TYPE_OPENOFFICE;
					} else {
						$documentationType = static::DOCUMENTATION_TYPE_UNKNOWN;
					}
					switch ($documentationType) {

						// ---------------------------------
						// Sphinx documentation
						// ---------------------------------
						case static::DOCUMENTATION_TYPE_SPHINX:
							echo ' [RENDER] ' . $extensionKey . ' ' . $version . ' (Sphinx project)' . "\n";

							// Clean-up render directory
							$this->cleanUpDirectory($renderDirectory);


							if (!is_file($versionDirectory . 'Documentation/Settings.yml')) {
								$this->createSettingsYml($versionDirectory, $extensionKey);
							}

							// Fix version/release in Settings.yml
							$this->overrideVersionAndReleaseInSettingsYml($versionDirectory, $version);

							$this->createConfPy(
								$extensionKey,
								$version,
								$renderDirectory,
								'Documentation/'
							);

							$this->createCronRebuildConf(
								$extensionKey,
								$version,
								$buildDirectory,
								$renderDirectory,
								$versionDirectory,
								'Documentation/'
							);

							$this->renderProject($renderDirectory);
							if (!is_file($buildDirectory . '/Index.html')) {
								echo '[WARNING] Cannot find file ' . $buildDirectory . '/Index.html' . "\n";
							} else {
								$this->addReference($extensionKey, $documentationType, $version, $versionDirectory, $buildDirectory);
								$this->updateListOfExtensions($extensionKey, $buildDirectory);
							}
							break;

						// ---------------------------------
						// README.rst documentation
						// ---------------------------------
						case static::DOCUMENTATION_TYPE_README:
							echo ' [RENDER] ' . $extensionKey . ' ' . $version . ' (simple README)' . "\n";

							// Clean-up render directory
							$this->cleanUpDirectory($renderDirectory);

							$this->createConfPy(
								$extensionKey,
								$version,
								$renderDirectory,
								'',
								'README'
							);

							$this->createCronRebuildConf(
								$extensionKey,
								$version,
								$buildDirectory,
								$renderDirectory,
								$versionDirectory,
								''
							);

							$this->renderProject($renderDirectory);
							if (!is_file($buildDirectory . '/Index.html')) {
								echo '[WARNING] Cannot find file ' . $buildDirectory . '/Index.html' . "\n";
							} else {
								$this->addReference($extensionKey, $documentationType, $version, $versionDirectory, $buildDirectory);
								$this->updateListOfExtensions($extensionKey, $buildDirectory);
							}
							break;

						// ---------------------------------
						// OpenOffice documentation
						// ---------------------------------
						case static::DOCUMENTATION_TYPE_OPENOFFICE:
							echo ' [RENDER] ' . $extensionKey . ' ' . $version . ' (OpenOffice)' . "\n";

							// Clean-up render directory
							$this->cleanUpDirectory($renderDirectory);

							// Convert OpenOffice to Sphinx
							$manualFilename = $versionDirectory . 'doc/manual.sxw';
							$cmd = 'python ' .
								dirname(__FILE__) . '/../../Resources/Private/Vendor/RestTools/T3PythonDocBuilderPackage/src/T3PythonDocBuilder/t3pdb_sxw2html.py ' .
								escapeshellarg($manualFilename) . ' ' .
								escapeshellarg($renderDirectory);
							exec($cmd);

							if (!is_file($renderDirectory . 't3pdb/Documentation/Index.rst')) {
								echo '  [ERROR] Conversion from manual.sxw failed' . "\n";
							} else {
								// Move the generated Sphinx project to the original extension directory
								exec('rm -rf ' . escapeshellarg($versionDirectory) . 'Documentation');
								exec('mv ' . escapeshellarg($renderDirectory . 't3pdb/Documentation') . ' ' . escapeshellarg($versionDirectory));

								if (!is_file($versionDirectory . 'Documentation/Includes.txt')) {
									// This file is often needed, and may crash the rendering if it is not there.
									// This is most probably a bug in the OOo converter
									exec('touch ' . escapeshellarg($versionDirectory . 'Documentation/Includes.txt'));
								}
								if (!is_file($versionDirectory . 'Documentation/Targets.rst')) {
									// This file is often needed, and may crash the rendering if it is not there.
									// This is most probably a bug in the OOo converter
									exec('touch ' . escapeshellarg($versionDirectory . 'Documentation/Targets.rst'));
								}

								// We now lack a Settings.yml file
								$this->createSettingsYml($versionDirectory, $extensionKey);

								// ---------------------------------
								// Sphinx from OOo documentation
								// ---------------------------------

								// Clean-up render directory
								$this->cleanUpDirectory($renderDirectory);

								// Fix version/release in Settings.yml
								$this->overrideVersionAndReleaseInSettingsYml($versionDirectory, $version);

								$this->createConfPy(
									$extensionKey,
									$version,
									$renderDirectory,
									'Documentation/'
								);

								$this->createCronRebuildConf(
									$extensionKey,
									$version,
									$buildDirectory,
									$renderDirectory,
									$versionDirectory,
									'Documentation/',
									FALSE
								);

								$this->renderProject($renderDirectory);
								if (!is_file($buildDirectory . '/Index.html')) {
									echo '[WARNING] Cannot find file ' . $buildDirectory . '/Index.html' . "\n";
								} else {
									$this->addReference($extensionKey, $documentationType, $version, $versionDirectory, $buildDirectory);
									$this->updateListOfExtensions($extensionKey, $buildDirectory);
								}
							}
							break;

						default:
							echo '[WARNING] Unknown documentation format: skipping rendering' . "\n";
							break;
					}
				}

				$this->removeFromQueue($extensionKey, $version);
				sleep(5);
			}

			// Put .htaccess for the extension if needed
			if (is_dir($baseBuildDirectory) && !is_file($baseBuildDirectory . '.htaccess')) {
				symlink(rtrim($GLOBALS['CONFIG']['DIR']['scripts'], '/') . '/config/_htaccess', $baseBuildDirectory . '.htaccess');
			}

		}

	}

	/**
	 * Overrides the version and release in Settings.yml (because developers simply tend to forget about
	 * adapting this info prior to uploading their extension to TER).
	 *
	 * @param string $path
	 * @param string $version
	 * @return void
	 */
	protected function overrideVersionAndReleaseInSettingsYml($path, $version) {
		$path = rtrim($path, '/') . '/';
		$filenames = array('Documentation/Settings.yml');

		// Search for other translated versions of Settings.yml
		$directories = $this->get_dirs($path . 'Documentation/');
		foreach ($directories as $directory) {
			if (preg_match('/^Localization\./', $directory)) {
				$localizationDirectory = $path . 'Documentation/' . $directory . '/Settings.yml';
				if (!is_file($localizationDirectory)) {
					copy($path . 'Documentation/Settings.yml', $localizationDirectory);
				}
				$filenames[] = 'Documentation/' . $directory . '/Settings.yml';
			}
		}

		// release is actually the "version" from TER
		$release = $version;
		// whereas version is a two digit alternative of the release number
		$parts = explode('.', $release);
		$version = $parts[0] . '.' . $parts[1];

		foreach ($filenames as $filename) {
			$contents = file_get_contents($path . $filename);
			$contents = preg_replace('/^(\s+version): (.*)/m', '\1: ' . $version, $contents);
			$contents = preg_replace('/^(\s+release): (.*)$/m', '\1: ' . $release, $contents);
			file_put_contents($path . $filename, $contents);
		}
	}

	/**
	 * Creates a default Settings.yml configuration file.
	 *
	 * @param string $extensionDirectory
	 * @param string $extensionKey
	 * @return void
	 */
	protected function createSettingsYml($extensionDirectory, $extensionKey) {
		$extensionDirectory = rtrim($extensionDirectory, '/') . '/';

		$_EXTKEY = $extensionKey;
		$EM_CONF = array();
		include($extensionDirectory . 'ext_emconf.php');
		$copyright = date('Y');
		$title = $EM_CONF[$_EXTKEY]['title'];

		$configuration = <<<YAML
# This is the project specific Settings.yml file.
# Place Sphinx specific build information here.
# Settings given here will replace the settings of 'conf.py'.

---
conf.py:
  copyright: $copyright
  project: $title
  version: 1.0
  release: 1.0.0
...

YAML;
		file_put_contents($extensionDirectory .  'Documentation/Settings.yml', $configuration);
	}

	/**
	 * Creates a conf.py configuration file.
	 *
	 * @param string $extensionKey
	 * @param string $version
	 * @param string $renderDirectory
	 * @param string $prefix Optional prefix directory ("Documentation/")
	 * @param string $masterDocument
	 * @return void
	 */
	protected function createConfPy($extensionKey, $version, $renderDirectory, $prefix, $masterDocument = 'Index') {
	    $replacements = array(
			'###DOCUMENTATION_RELPATH###' => '../queue/' . $extensionKey . '/' . $version . '/' . $prefix,
			'###MASTER_DOC###' => $masterDocument,
		);
		$contents = file_get_contents(dirname(__FILE__) . '/../../Resources/Private/Templates/conf.py');
		$contents = str_replace(
			array_keys($replacements),
			array_values($replacements),
			$contents
		);
		file_put_contents($renderDirectory . 'conf.py', $contents);
	}

	/**
	 * Creates a cron_rebuild.conf configuration file.
	 *
	 * @param string $extensionKey
	 * @param string $version
	 * @param string $buildDirectory
	 * @param string $renderDirectory
	 * @param string $versionDirectory
	 * @param string $prefix Optional prefix directory ("Documentation/")
	 * @param boolean $createArchive
	 * @return void
	 */
	protected function createCronRebuildConf($extensionKey, $version, $buildDirectory, $renderDirectory, $versionDirectory, $prefix, $createArchive = TRUE) {
		$packageZip = $createArchive ? '1' : '0';

		$contents = <<<EOT
PROJECT=$extensionKey
VERSION=$version

# Where to publish documentation
BUILDDIR=$buildDirectory

# If GITURL is empty then GITDIR is expected to be "ready" to be processed
GITURL=
GITDIR=$renderDirectory
GITBRANCH=

# Path to the documentation within the Git repository
T3DOCDIR=${versionDirectory}${prefix}

# Packaging information
PACKAGE_ZIP=$packageZip
PACKAGE_KEY=typo3cms.extensions.$extensionKey
PACKAGE_LANGUAGE=default
EOT;

		file_put_contents($renderDirectory . 'cron_rebuild.conf', $contents);
	}

	/**
	 * Renders a Sphinx project.
	 *
	 * @param string $renderDirectory
	 * @return void
	 */
	protected function renderProject($renderDirectory) {
		symlink(rtrim($GLOBALS['CONFIG']['DIR']['scripts'], '/') . '/config/Makefile', $renderDirectory . 'Makefile');
		symlink(rtrim($GLOBALS['CONFIG']['DIR']['scripts'], '/') . '/bin/cron_rebuild.sh', $renderDirectory . 'cron_rebuild.sh');

		// Invoke rendering
		$cmd = 'cd ' . $renderDirectory . ' && touch REBUILD_REQUESTED && ./cron_rebuild.sh';
		exec($cmd);

		// TODO? Copy warnings*.txt + possible pdflatex log to output directory
	}

	/**
	 * Adds a reference to the documentation (e.g., used by EXT:sphinx).
	 *
	 * @param string $extensionKey
	 * @param string $format
	 * @param string $version
	 * @param string $extensionDirectory
	 * @param string $buildDirectory
	 * @return void
	 */
	protected function addReference($extensionKey, $format, $version, $extensionDirectory, $buildDirectory) {
		$extensionDirectory = rtrim($extensionDirectory, '/') . '/';
		$buildDirectory = rtrim($buildDirectory, '/');	// No trailing slash here!
		$referenceFilename = rtrim($GLOBALS['CONFIG']['DIR']['publish'], '/') . '/manuals.json';
		$references = array();
		if (is_file($referenceFilename)) {
			$references = json_decode(file_get_contents($referenceFilename), TRUE);
			if (!is_array($references)) {
				$references = array();
			}
		}

		$references[$extensionKey] = array(
			'lastupdated' => time(),
			'format' => $format,
			'version' => $version,
		);

		if ($format == static::DOCUMENTATION_TYPE_SPHINX) {
			if (count(glob($buildDirectory . '/_pdf/*.pdf')) > 0) {
				$references[$extensionKey]['pdf'][] = 'default';
			}

			$directories = $this->get_dirs($extensionDirectory . 'Documentation/');
			foreach ($directories as $directory) {
				if (preg_match('/^Localization\.(.*)/', $directory, $matches)) {
					$locale = str_replace('_', '-', strtolower($matches[1]));
					$version = basename($buildDirectory);
					$localeDirectory = $buildDirectory . '/../' . $locale . '/' . $version . '/';
					if (is_file($localeDirectory . 'Index.html')) {
						$references[$extensionKey]['localizations'][] = $matches[1];

						if (count(glob($localeDirectory . '_pdf/*.pdf')) > 0) {
							$references[$extensionKey]['pdf'][] = $matches[1];
						}
					}
				}
			}
		}

		ksort($references);
		file_put_contents($referenceFilename, json_encode($references));
	}

	/**
	 * Updates the list of extensions in "extensions.js".
	 *
	 * @param string $extensionKey
	 * @param string $directory Build directory of the last rendered documentation (thus incl. version number at the end)
	 * @return void
	 */
	protected function updateListOfExtensions($extensionKey, $directory, $refresh = FALSE) {
		$extensionsJsFilename = rtrim($GLOBALS['CONFIG']['DIR']['publish'], '/') . '/extensions.js';
		$extensions = array();
		if (is_file($extensionsJsFilename)) {
			$content = file_get_contents($extensionsJsFilename);
			$declaration = 'var extensionList =';
			// Cut to beginning of JSON string
			$content = trim(substr($content, strpos($content, $declaration) + strlen($declaration)));
			// Cut from end of JSON string (trailing semicolon)
			$content = substr($content, 0, -1);
			if ($content{0} === '[') {
				$extensions = json_decode($content, TRUE);
				if ($extensions === NULL) {
					// Something went wrong, we do not want to further corrupt the file
					echo '[WARNING] File ' . $extensionsJsFilename . ' cannot be decoded, please investigate and fix it.' . "\n";
					return;
				}
				$numberOfExtensions = count($extensions);
				$list = array();
				for ($i = 0; $i < $numberOfExtensions; $i++) {
					$list[$extensions[$i]['key']] = $extensions[$i];
				}
				$extensions = $list;
				unset($list);
				if ($refresh) {
					$exts = array_keys($extensions);
					foreach ($exts as $ext) {
						$extDir = rtrim($GLOBALS['CONFIG']['DIR']['publish'], '/') . '/' . $ext;
						if (is_dir($extDir)) {
							echo '   [INFO] Refreshing versions of ' . $ext . "\n";
							$this->updateListOfExtensions($ext, $extDir . '/latest');
						}
					}
					return;
				}
			}
		} else {
			// TODO: initialize this file by searching for every existing extensions and versions?
		}
		if (count($extensions) === 0) {
			return;
		}

		$versions = $this->get_dirs(dirname($directory));
		$versions = array_flip($versions);

		// No real versions
		unset($versions['packages']);
		unset($versions['stable']);

		$hasLatest = isset($versions['latest']);
		unset($versions['latest']);
		$versions = array_flip($versions);

		// Remove localizations
		for ($i = 0; $i < count($versions); $i++) {
			if (!preg_match('/^[0-9]/', $versions[$i])) {
				unset($versions[$i]);
			}
		}

		// Reverse sort the list of versions
		usort($versions, function($a, $b) {
			return version_compare($b, $a);
		});

		if ($hasLatest) {
			array_unshift($versions, 'latest');
		}

		$extensions[$extensionKey] = array(
			'key' => $extensionKey,
			'latest' => $versions[0],
			'versions' => $versions,
		);

		// Sort by extension key
		ksort($extensions);

		$content = '// BEWARE: this file has been automatically generated by ' . __CLASS__ . "\n";
		$content .= '// on ' . date('d.m.Y H:i:s') . "\n";
		$content .= '// DO NOT MODIFY MANUALLY' . "\n";
		$content .= $declaration . ' ';

		$json = json_encode(array_values($extensions));
		// Prettify a bit the JSON (without making it too verbose if we would use built-in feature of PHP 5.4)
		$json = "[\n\t" . substr($json, 1, -1) . "\n]";
		$json = str_replace('},', "},\n\t", $json);

		$content .= $json . ';';

		file_put_contents($extensionsJsFilename, $content);
	}

	/**
	 * Cleans-up a directory.
	 *
	 * @param string $path
	 * @return void
	 */
	protected function cleanUpDirectory($path) {
		exec('rm -rf ' . escapeshellarg($path));
		exec('mkdir -p ' . escapeshellarg($path));
	}

	/**
	 * Removes an extensionKey/version pair from the rendering queue.
	 *
	 * @param string $extensionKey
	 * @param string $version
	 * @return void
	 */
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
	protected function get_dirs($path) {
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


