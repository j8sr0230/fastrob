from typing import cast

import FreeCAD as App
import Part


class SliceObject:
	def __init__(self, obj: Part.Feature) -> None:
		obj.addProperty("App::PropertyLength", "Length", "Dimensions", "Length of the box").Length = 10.
		obj.addProperty("App::PropertyLength", "Width", "Dimensions", "Width of the box").Width = 10.
		obj.addProperty("App::PropertyLength", "Height", "Dimensions", "Height of the box").Height = 10.
		obj.Proxy = self

	# noinspection PyPep8Naming, PyMethodMayBeStatic, PyUnresolvedReferences
	def execute(self, fp: Part.Feature) -> None:
		fp.Shape = Part.makeBox(fp.Length, fp.Width, fp.Height)

	# noinspection PyPep8Naming, PyMethodMayBeStatic, PyUnusedLocal, PyUnresolvedReferences
	def onChanged(self, fp: Part.Feature, prop: str) -> None:
		if prop == "Length" or prop == "Width" or prop == "Height":
			fp.Shape = Part.makeBox(fp.Length, fp.Width, fp.Height)


slice_doc_obj: Part.Feature = cast(Part.Feature, App.ActiveDocument.addObject("Part::FeaturePython", "Slice"))
SliceObject(slice_doc_obj)
slice_doc_obj.ViewObject.Proxy = 0
