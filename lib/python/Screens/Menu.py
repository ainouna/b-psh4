from Screen import Screen
from Screens.ParentalControlSetup import ProtectedScreen
from Components.Sources.List import List
from Components.ActionMap import NumberActionMap
from Components.Sources.StaticText import StaticText
from Components.config import configfile
from Components.PluginComponent import plugins
from Components.config import config
from Components.SystemInfo import SystemInfo

from Tools.BoundFunction import boundFunction
from Tools.Directories import resolveFilename, fileExists, SCOPE_SKIN, SCOPE_CONFIG

import xml.etree.cElementTree

from Screens.Setup import Setup, getSetupTitle

# read the menu
menu = resolveFilename(SCOPE_CONFIG, 'menu.xml')
if not fileExists(menu):
	menu = resolveFilename(SCOPE_SKIN, 'menu.xml')
mdom = xml.etree.cElementTree.parse(menu)

class MenuUpdater:
	def __init__(self):
		self.updatedMenuItems = {}

	def addMenuItem(self, id, pos, text, module, screen, weight):
		if not self.updatedMenuAvailable(id):
			self.updatedMenuItems[id] = []
		self.updatedMenuItems[id].append([text, pos, module, screen, weight])

	def delMenuItem(self, id, pos, text, module, screen, weight):
		self.updatedMenuItems[id].remove([text, pos, module, screen, weight])

	def updatedMenuAvailable(self, id):
		return self.updatedMenuItems.has_key(id)

	def getUpdatedMenu(self, id):
		return self.updatedMenuItems[id]

menuupdater = MenuUpdater()

class MenuSummary(Screen):
	pass

class Menu(Screen, ProtectedScreen):
	ALLOW_SUSPEND = True

	def okbuttonClick(self):
		print "okbuttonClick"
		selection = self["menu"].getCurrent()
		if selection is not None:
			selection[1]()

	def execText(self, text):
		exec text

	def runScreen(self, arg):
		# arg[0] is the module (as string)
		# arg[1] is Screen inside this module
		#        plus possible arguments, as
		#        string (as we want to reference
		#        stuff which is just imported)
		# FIXME. somehow
		if str(arg[0]).find("Screens.Bh") != -1:
			self.openBhMenu(arg[0])
		else:
			if arg[0] != "":
				exec "from " + arg[0] + " import *"

			self.openDialog(*eval(arg[1]))

	def openBhMenu(self, module):
		exec "from " + module + " import *"
		
		if module == "Screens.BhSettings":
			self.session.openWithCallback(self.menuClosed, DeliteSettings)
		
		elif module == "Screens.BhEpgPanel":
			self.session.openWithCallback(self.menuClosed, DeliteEpgPanel)
			
		elif module == "Screens.BhAddons":
			self.session.openWithCallback(self.menuClosed, DeliteAddons)
		
		elif module == "Screens.BhRed":
			exec "from Screens.BhUtils import BhU_check_proc_version"
			flash = True
			mounted = False
			bh_ver = BhU_check_proc_version()
			un_ver = bh_ver
		
			f = open("/proc/mounts",'r')
			for line in f.readlines():
				if line.find('/universe') != -1:
					if line.find('ext') != -1:
						mounted = True
			f.close()
		
			if fileExists("/.meoinfo"):
				flash = False
		
			if flash == True:
				if mounted == True:
					if fileExists("/universe/.buildv"):
						f = open("/universe/.buildv",'r')
						un_ver = f.readline().strip()
						f.close()
					else:
						out = open("/universe/.buildv",'w')
						out.write(bh_ver)
						out.close()
						system("chmod a-w /universe/.buildv")
					if un_ver == bh_ver:
						self.session.openWithCallback(self.menuClosed, BhRedPanel)
					else:
						self.session.openWithCallback(self.menuClosed, BhRedWrong)
				else:
					self.session.openWithCallback(self.menuClosed, BhRedDisabled, "0")
			else:
				self.session.openWithCallback(self.menuClosed, BhRedDisabled, "flash")

	def nothing(self): #dummy
		pass

	def openDialog(self, *dialog):				# in every layer needed
		self.session.openWithCallback(self.menuClosed, *dialog)

	def openSetup(self, dialog):
		self.session.openWithCallback(self.menuClosed, Setup, dialog)

	def addMenu(self, destList, node):
		requires = node.get("requires")
		if requires:
			if requires[0] == '!':
				if SystemInfo.get(requires[1:], False):
					return
			elif not SystemInfo.get(requires, False):
				return
		MenuTitle = _(node.get("text", "??").encode("UTF-8"))
		entryID = node.get("entryID", "undefined")
		weight = node.get("weight", 50)
		x = node.get("flushConfigOnClose")
		if x:
			a = boundFunction(self.session.openWithCallback, self.menuClosedWithConfigFlush, Menu, node)
		else:
			a = boundFunction(self.session.openWithCallback, self.menuClosed, Menu, node)
		#TODO add check if !empty(node.childNodes)
		destList.append((MenuTitle, a, entryID, weight))

	def menuClosedWithConfigFlush(self, *res):
		configfile.save()
		self.menuClosed(*res)

	def menuClosed(self, *res):
		if res and res[0]:
			self.close(True)

	def addItem(self, destList, node):
		requires = node.get("requires")
		if requires:
			if requires[0] == '!':
				if SystemInfo.get(requires[1:], False):
					return
			elif not SystemInfo.get(requires, False):
				return
		configCondition = node.get("configcondition")
		if configCondition and not eval(configCondition + ".value"):
			return
		item_text = node.get("text", "").encode("UTF-8")
		entryID = node.get("entryID", "undefined")
		weight = node.get("weight", 50)
		for x in node:
			if x.tag == 'screen':
				module = x.get("module")
				screen = x.get("screen")

				if screen is None:
					screen = module

				print module, screen
				if module:
					module = "Screens." + module
				else:
					module = ""

				# check for arguments. they will be appended to the
				# openDialog call
				args = x.text or ""
				screen += ", " + args

				destList.append((_(item_text or "??"), boundFunction(self.runScreen, (module, screen)), entryID, weight))
				return
			elif x.tag == 'code':
				destList.append((_(item_text or "??"), boundFunction(self.execText, x.text), entryID, weight))
				return
			elif x.tag == 'setup':
				id = x.get("id")
				if item_text == "":
					item_text = _(getSetupTitle(id))
				else:
					item_text = _(item_text)
				destList.append((item_text, boundFunction(self.openSetup, id), entryID, weight))
				return
		destList.append((item_text, self.nothing, entryID, weight))


	def __init__(self, session, parent):
		Screen.__init__(self, session)
		list = []

		menuID = None
		for x in parent:						#walk through the actual nodelist
			if not x.tag:
				continue
			if x.tag == 'item':
				item_level = int(x.get("level", 0))
				if item_level <= config.usage.setup_level.index:
					self.addItem(list, x)
					count += 1
			elif x.tag == 'menu':
				self.addMenu(list, x)
				count += 1
			elif x.tag == "id":
				menuID = x.get("val")
				count = 0

			if menuID is not None:
				# menuupdater?
				if menuupdater.updatedMenuAvailable(menuID):
					for x in menuupdater.getUpdatedMenu(menuID):
						if x[1] == count:
							list.append((x[0], boundFunction(self.runScreen, (x[2], x[3] + ", ")), x[4]))
							count += 1

		if menuID is not None:
			# plugins
			for l in plugins.getPluginsForMenu(menuID):
				# check if a plugin overrides an existing menu
				plugin_menuid = l[2]
				for x in list:
					if x[2] == plugin_menuid:
						list.remove(x)
						break
				list.append((l[0], boundFunction(l[1], self.session, close=self.close), l[2], l[3] or 50))

		# for the skin: first try a menu_<menuID>, then Menu
		self.skinName = [ ]
		if menuID is not None:
			self.skinName.append("menu_" + menuID)
		self.skinName.append("Menu")
		self.menuID = menuID
		ProtectedScreen.__init__(self)

		# Sort by Weight
		list.sort(key=lambda x: int(x[3]))

		self["menu"] = List(list)

		self["actions"] = NumberActionMap(["OkCancelActions", "MenuActions", "NumberActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.closeNonRecursive,
				"menu": self.closeRecursive,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal
			})

		a = parent.get("title", "").encode("UTF-8") or None
		a = a and _(a)
		if a is None:
			a = _(parent.get("text", "").encode("UTF-8"))
		self["title"] = StaticText(a)
		self.menu_title = a

	def keyNumberGlobal(self, number):
		print "menu keyNumber:", number
		# Calculate index
		number -= 1

		if len(self["menu"].list) > number:
			self["menu"].setIndex(number)
			self.okbuttonClick()

	def closeNonRecursive(self):
		self.close(False)

	def closeRecursive(self):
		self.close(True)

	def createSummary(self):
		return MenuSummary

	def isProtected(self):
		if config.ParentalControl.setuppinactive.value:
			if config.ParentalControl.config_sections.main_menu.value and not(hasattr(self.session, 'infobar') and self.session.infobar is None):
				return self.menuID == "mainmenu"
			elif config.ParentalControl.config_sections.configuration.value and self.menuID == "setup":
				return True
			elif config.ParentalControl.config_sections.standby_menu.value and self.menuID == "shutdown":
				return True
class MainMenu(Menu):
	#add file load functions for the xml-file

	def __init__(self, *x):
		self.skinName = "Menu"
		Menu.__init__(self, *x)