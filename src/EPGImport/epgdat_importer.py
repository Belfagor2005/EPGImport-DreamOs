from __future__ import absolute_import, print_function
from os import popen, access, W_OK
from os.path import join, ismount
from sys import platform
from . import epgdat


# Hack to make this test run on Windows (where the reactor cannot handle files)
if platform.startswith("win"):
	tmppath = "."
	settingspath = "."
else:
	tmppath = "/tmp"
	settingspath = "/etc/enigma2"


def getMountPoints():
	mount_points = []
	try:
		with open('/proc/mounts', 'r') as mounts:
			for line in mounts:
				parts = line.split()
				mount_point = parts[1]
				if ismount(mount_point) and access(mount_point, W_OK):
					mount_points.append(mount_point)
	except Exception as e:
		print("[EPGImport] Error reading /proc/mounts:", e)
	return mount_points


mount_points = getMountPoints()


class epgdatclass:
	def __init__(self):
		self.data = None
		self.services = None
		path = tmppath
		for p in ["/media/cf", "/media/mmc", "/media/usb", "/media/hdd"]:
			if self.checkPath(p):
				path = p
				break

		self.epgfile = join(path, "epg_new.dat")
		self.epg = epgdat.epgdat_class(path, settingspath, self.epgfile)

	def importEvents(self, services, dataTupleList):
		'''This method is called repeatedly for each bit of data'''
		if services != self.services:
			self.commitService()
			self.services = services
		for program in dataTupleList:
			if program[3]:
				desc = program[3] + '\n' + program[4]
			else:
				desc = program[4]
			self.epg.add_event(program[0], program[1], program[2], desc)

	def commitService(self):
		if self.services is not None:
			self.epg.preprocess_events_channel(self.services)

	def epg_done(self):
		try:
			self.commitService()
			self.epg.final_process()
		except:
			print("[EPGImport] Failure in epg_done")
			import traceback
			traceback.print_exc()
		self.epg = None

	def checkPath(self, path):
		f = popen("mount", "r")
		for ln in f:
			if ln.find(path) != - 1:
				return True
		return False

	def __del__(self):
		"""Destructor - finalize the file when done"""
		if self.epg is not None:
			self.epg_done()
