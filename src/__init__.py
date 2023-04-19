import sys
import os
import json
import toml
import shutil
import dpath
import stat
from tempfile import TemporaryDirectory
from subprocess import call
from git import Repo
from typing import TypedDict, Literal

WALLY_PATH = "wally.toml"
WALLY_INDEX_OWNER = "UpliftGames"
WALLY_INDEX_NAME = "wally-index"

UpgradeFocus = Literal["major", "minor", "patch"]

class WallyConfigInfo(TypedDict):
	name: str
	version: str
	registry: str
	realm: str

class WallyConfig(TypedDict):
	package: WallyConfigInfo
	dependencies: dict[str, str]

class PackageInfoData(TypedDict):
	name: str
	version: str
	registry: str
	realm: str
	description: str
	license: None | str
	authors: list[str]
	include: list[str]
	exclude: list[str]
	private: bool

class PlaceInfoData(TypedDict):
	shared_packages: bool
	server_packages: bool

class WallyPackageData(TypedDict):
	package: PackageInfoData
	place: PlaceInfoData
	dependencies: str
	server_dependencies: str
	dev_dependencies: str

def download_repo(owner: str, name: str, out_path: str):

	# Download wally index
	if os.path.exists(out_path):
		shutil.rmtree(out_path)
		
	Repo.clone_from("https://github.com/"+owner+"/"+name+".git", out_path, branch='main', depth=1)

	#from: https://stackoverflow.com/questions/4829043/how-to-remove-read-only-attrib-directory-with-python-in-windows
	for file_name in os.listdir(out_path):
			
		def on_rm_error(func, path, exc_info):	
			os.chmod(path, stat.S_IWRITE)
			os.unlink(path)

		if file_name.endswith('git'):
			file_path = os.path.join(out_path, file_name)
			# We want to unhide the .git folder before unlinking it.
			while True:
				call(['attrib', '-H', file_path])
				break
			shutil.rmtree(file_path, onerror=on_rm_error)

def get_wally_index() -> dict[str, dict[str, list[WallyPackageData]]]:
	with TemporaryDirectory() as temp_dir_path:
		wally_index_path = temp_dir_path + "/wally_index"
		download_repo(WALLY_INDEX_OWNER, WALLY_INDEX_NAME, wally_index_path)
		
		out = {}

		for domain_name in os.listdir(wally_index_path):
			full_domain_path = wally_index_path+"/"+domain_name
			domain_base, domain_ext = os.path.splitext(full_domain_path)
			out[domain_name] = {}
			if domain_ext != ".json":
				for file_name in os.listdir(full_domain_path):
					full_file_path = full_domain_path+"/"+file_name
					base, ext_name = os.path.splitext(full_file_path)
					
					if ext_name != ".json":
						package_file = open(full_file_path, "r", encoding="utf-8")
						out[domain_name][file_name] = []
						for entry in package_file.read().split("{\"package\""):
							if len(entry) > 0:
								out[domain_name][file_name].append(json.loads("{\"package\""+entry))

						version_list = []
						for version_data in out[domain_name][file_name]:
							file_data = {}
							for path, val in dpath.search(version_data, '**', yielded=True):
								if type(val) != dict and type(val) != list:
									formatted_path = path.replace(".", "").replace("-", "_").replace(" ", "")
									if type(val) == str:
										formatted_value = val.replace("\"", "")
										dpath.new(file_data, formatted_path, formatted_value)
									else:
										dpath.new(file_data, formatted_path, val)
							version_list.append(file_data)
						out[domain_name][file_name] = version_list

						package_file.close()
		return out

def get_best_path(package_path: str, upgrade_focus: UpgradeFocus, wally_index: dict[str, dict[str, list[WallyPackageData]]]) -> str:
	if not "@" in package_path:
		return package_path

	if "-" in package_path.split("@")[1]:
		return package_path

	address = package_path.split("@")[0]
	domain = address.split("/")[0]
	package_name = address.split("/")[1]
	version_str = (package_path.split("@")[1])
	values = version_str.split(".")
	major = int(values[0])
	minor = int(values[1])
	patch = int(values[2])

	best_major = major
	best_minor = minor
	best_patch = patch

	for package_option in wally_index[domain][package_name]:
		option_version_str = package_option["package"]["version"]
		if not "-" in option_version_str:
			option_values = option_version_str.split(".")
			option_major = int(option_values[0])
			option_minor = int(option_values[1])
			option_patch = int(option_values[2])
			if upgrade_focus == "major":
				if option_major > best_major:
					best_major = option_major
					best_minor = option_minor
					best_patch = option_patch
				elif option_major == best_major and option_minor > best_minor:
					best_minor = option_minor
					best_patch = option_patch
				elif option_major == best_major and option_minor == best_minor and option_patch > best_patch:
					best_patch = option_patch	
			elif upgrade_focus == "minor":
				if option_major == best_major and option_minor > best_minor:
					best_minor = option_minor
					best_patch = option_patch
				elif option_major == best_major and option_minor == best_minor and option_patch > best_patch:
					best_patch = option_patch	
			else:
				if option_major == best_major and option_minor == best_minor and option_patch > best_patch:
					best_patch = option_patch

	return f"{domain}/{package_name}@{best_major}.{best_minor}.{best_patch}"


def get_wally_config() -> WallyConfig:
	config_file = open(WALLY_PATH, "r")
	wally_config = toml.loads(config_file.read())
	config_file.close()
	return wally_config

def set_wally_config(wally_config: WallyConfig):
	config_file = open(WALLY_PATH, "w")
	config_file.write(toml.dumps(wally_config))
	config_file.close()

def main():
	focus: UpgradeFocus = "patch"
	if len(sys.argv) > 1:
		focus = sys.argv[1]

	wally_config = get_wally_config()
	wally_index = get_wally_index()

	is_different = False

	for name, path in wally_config["dependencies"].items():
		new_path = get_best_path(path, focus, wally_index)
		if new_path != path:
			is_different = True
			wally_config["dependencies"][name] = new_path

	if is_different:
		set_wally_config(wally_config)
		os.system("wally install")

main()