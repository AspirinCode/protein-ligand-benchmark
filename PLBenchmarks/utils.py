"""
utils.py
Contains utility functions
"""

import numpy as np
from scipy import constants
import urllib
import json
from pint import UnitRegistry

import warnings

ureg = UnitRegistry()

BOLTZMANN = constants.gas_constant * ureg("J / mole / K")


def findPdbUrl(pdb):
    """
    Finds the links to a pdb or a list of pdb codes.

    :param pdb: string
    :return: string compiled string including the urls to the pdb entries
    """

    if pdb is None:
        return ""
    url = "http://www.rcsb.org/pdb/rest/search"
    query_text = f'\
<orgPdbCompositeQuery version="1.0">\
 <queryRefinement>\
   <queryRefinementLevel>0</queryRefinementLevel>\
      <orgPdbQuery>\
        <version>head</version>\
        <queryType>org.pdb.query.simple.StructureIdQuery</queryType>\
        <structureIdList>{pdb}</structureIdList>\
      </orgPdbQuery>\
 </queryRefinement>\
</orgPdbCompositeQuery>\
'
    request = urllib.request.Request(url, data=query_text.encode())
    try:
        response = urllib.request.urlopen(request)
        page = response.read()
        page = page.decode("utf-8").split()
        res = []
        pdbs = pdb.split()
        for p in page:
            res.append("REP1http://www.rcsb.org/structure/{}REP2{}REP3".format(p, p))
        for p in pdbs:
            if p not in page:
                warnings.warn(f"PDB {p} not found")
    except urllib.error.URLError as e:
        warnings.warn(f"Could not find PDB {pdb}\n{e}")
        res = pdb.split()
    return ("\n").join(res)


def findDoiUrl(doi):
    """
    Finds the links to a digital object identifier (doi).

    :param doi: string
    :return: string compiled string including the urls to the publication
    """

    url = "https://api.crossref.org/works/" + str(doi)
    request = urllib.request.Request(url)
    try:
        response = urllib.request.urlopen(request)
        page = response.read().decode("utf-8")
        obj = json.loads(page)
        if obj["status"] == "ok":
            obj = obj["message"]
        aut = obj["author"]
        if len(aut) > 0:
            aut = obj["author"][0]["family"]
        else:
            aut = ""
        tit = obj["short-container-title"]
        if len(tit) > 0:
            tit = tit[0]
        else:
            tit = ""
        if "published-print" in obj.keys():
            dat = obj["published-print"]["date-parts"][0][0]
        else:
            dat = "XXXX"
        desc_string = "{} et al., {} {}".format(
            aut, tit, dat
        )  # , obj['journal-issue']['published-online']['date-parts'][0][0])
        result = f'REP1{obj["URL"]}REP2{desc_string}REP3'
    except urllib.error.URLError as e:
        warnings.warn(f"Could not find DOI: {doi}\n{e}")
        result = doi
    return result


def convertValue(val, originalObs, finalObs, temperature=300.0, outUnit=None):
    """
    Converts an experimental value into another derived quantity with specified unit.

    :param val: float, numerical value
    :param originalObs: string, code for the original observable. Can be `dg`, `ki`, `ic50`, `pic50`
    :param finalObs: string, code for the desired derived quantity. Can be `dg`, `ki`, `ic50`, `pic50`
    :param temperature: float, temperature in kelvin
    :param outUnit: unit of type :py:class:`pint`, output unit of finalObs, needs to fit to the requested finalObs
    :return: :py:class:`pint.Quantity` with desired unit
    """

    # define default units
    if outUnit is None:
        if finalObs == "dg":
            outUnit = ureg("kilocalories / mole")
        elif finalObs == "ki":
            outUnit = ureg("nanomolar")
        elif finalObs == "ic50":
            outUnit = ureg("nanomolar")
        elif finalObs == "pic50":
            outUnit = ureg("")

    if originalObs == "dg":
        if finalObs == "dg":
            return val.to(outUnit)
        elif finalObs == "ki":
            result = np.exp(-val / (BOLTZMANN * temperature * ureg.kelvin)) * ureg.molar
            return result.to(outUnit)
        elif finalObs == "ic50":
            result = np.exp(-val / (BOLTZMANN * temperature * ureg.kelvin)) * ureg.molar
            return result.to(outUnit)
        elif finalObs == "pic50":
            result = val / (BOLTZMANN * temperature * ureg.kelvin) / np.log(10)
            return result.to(outUnit)
        else:
            raise NotImplementedError
    elif originalObs == "ki":
        if finalObs == "dg":
            if val < 1e-15 * ureg("molar"):
                return 0.0 * outUnit
            else:
                result = (
                    BOLTZMANN * temperature * ureg.kelvin * np.log(val / ureg.molar)
                )
                return result.to(outUnit).round(2)
        elif finalObs == "ki":
            return val.to(outUnit)
        elif finalObs == "ic50":
            return val.to(outUnit)
        elif finalObs == "pic50":
            if val < 1e-15 * ureg("molar"):
                return -1e15 * outUnit
            else:
                result = -np.log(val / ureg.molar) / np.log(10)
                return result
        else:
            raise NotImplementedError
    elif originalObs == "ic50":
        if finalObs == "dg":
            if val < 1e-15 * ureg("molar"):
                return 0.0 * outUnit
            else:
                result = (
                    BOLTZMANN
                    * temperature
                    * ureg.kelvin
                    * np.log(val.to("molar") / ureg.molar)
                )
                return result.to(outUnit).round(2)
        elif finalObs == "ki":
            return val.to(outUnit)
        elif finalObs == "ic50":
            return val.to(outUnit)
        elif finalObs == "pic50":
            if val.to("molar") < 1e-15 * ureg("molar"):
                return -1e15 * outUnit
            else:
                result = -np.log(val / ureg.molar) / np.log(10)
                return result
        else:
            raise NotImplementedError
    elif originalObs == "pic50":
        if finalObs == "dg":
            result = -BOLTZMANN * temperature * ureg.kelvin * val * np.log(10)
            return result.to(outUnit).round(2)
        elif finalObs == "ki":
            result = 10 ** (-val) * ureg("molar")
            return result.to(outUnit)
        elif finalObs == "ic50":
            result = 10 ** (-val) * ureg("molar")
            return result.to(outUnit)
        elif finalObs == "pic50":
            return val.to(outUnit)
        else:
            raise NotImplementedError


def convertError(eVal, val, originalObs, finalObs, temperature=300.0, outUnit=None):
    """
    Converts an experimental value into another derived quantity with specified unit.

    :param eVal: float, error of val, numerical value
    :param val: float, numerical value
    :param originalObs: string, code for the original observable. Can be `dg`, `ki`, `ic50`, `pic50`
    :param finalObs: string, code for the desired derived quantity. Can be `dg`, `ki`, `ic50`, `pic50`
    :param temperature: float, temperature in kelvin
    :param outUnit: unit of type :py:class:`pint`, output unit of finalObs, needs to fit to the requested finalObs
    :return: :py:class:`pint.Quantity` with desired unit
    """

    # define default units
    if outUnit is None:
        if finalObs == "dg":
            outUnit = ureg("kilocalories / mole")
        elif finalObs == "ki":
            outUnit = ureg("nanomolar")
        elif finalObs == "ic50":
            outUnit = ureg("nanomolar")
        elif finalObs == "pic50":
            outUnit = ureg("")

    if originalObs == "dg":
        if finalObs == "dg":
            return eVal.to(outUnit)
        elif finalObs == "ki":
            # e_ki^2 = (del K/del dG)^2 * e_dG^2
            # e_ki   = 1/RT * exp(-dG/RT) * e_dG
            kBT = BOLTZMANN * temperature * ureg.kelvin
            error = 1.0 / kBT * np.exp(-val / kBT) * eVal * ureg.molar
            return error.to(outUnit)
        elif finalObs == "ic50":
            kBT = BOLTZMANN * temperature * ureg.kelvin
            error = 1.0 / kBT * np.exp(-val / kBT) * eVal * ureg.molar
            return error.to(outUnit)
        elif finalObs == "pic50":
            # e_pic50^2 = (del pic50/del dG)^2 * e_dG^2
            # e_pic50   = 1/(RT*ln(10)) * e_dG
            kBT = BOLTZMANN * temperature * ureg.kelvin
            error = 1.0 / (kBT * np.log(10)) * eVal
            return error.to(outUnit)
        else:
            raise NotImplementedError
    elif originalObs == "ki":
        if finalObs == "dg":
            if val < 1e-15 * ureg.molar:
                return 0.0 * outUnit
            else:
                error = BOLTZMANN * temperature * ureg.kelvin / val * eVal
                return error.to(outUnit).round(2)
        elif finalObs == "ki":
            return eVal.to(outUnit)
        elif finalObs == "ic50":
            return eVal.to(outUnit)
        elif finalObs == "pic50":
            # e_pic50^2 = (del pic50/del Ki)^2 * e_Ki^2
            # e_pic50   = 1/(Ki*ln(10)) * e_Ki
            if (val * np.log(10)) < 1e-15 * ureg("molar"):
                return 1e15 * outUnit
            else:
                result = 1 / (val * np.log(10)) * eVal
                return result.to(outUnit).round(2)
        else:
            raise NotImplementedError
    elif originalObs == "ic50":
        if finalObs == "dg":
            if val < 1e-15 * ureg.molar:
                return 0.0 * outUnit
            else:
                error = BOLTZMANN * temperature * ureg.kelvin / val * eVal
                return error.to(outUnit).round(2)
        elif finalObs == "ki":
            return eVal.to(outUnit)
        elif finalObs == "ic50":
            return eVal.to(outUnit)
        elif finalObs == "pic50":
            # e_pic50^2 = (del pic50/del IC50)^2 * e_IC50^2
            # e_pic50   = 1/(IC50*ln(10)) * e_IC50
            if (val * np.log(10)) < 1e-15 * ureg("molar"):
                return 1e15 * outUnit
            else:
                result = 1 / (val * np.log(10)) * eVal
                return result.to(outUnit).round(2)
        else:
            raise NotImplementedError
    elif originalObs == "pic50":
        if finalObs == "dg":
            error = BOLTZMANN * temperature * ureg.kelvin * np.log(10) * eVal
            return error.to(outUnit).round(2)
        elif finalObs == "ki":
            # Ki = 10^(-pIC50)
            # dKi^2 = (del Ki / del pIC50)^2 * dpIC50^2
            # dKi = ln(10) * 10^(-pIC50) * dpIC50
            error = np.log(10) * 10 ** (-val) * eVal * ureg("molar")
            return error.to(outUnit).round(2)
        elif finalObs == "ic50":
            # IC50 = 10^(-pIC50)
            # dIC50^2 = (del IC50 / del pIC50)^2 * dpIC50^2
            # dIC50 = ln(10) * 10^(-pIC50) * dpIC50
            error = np.log(10) * 10 ** (-val) * eVal * ureg("molar")
            return error.to(outUnit).round(2)
        elif finalObs == "pic50":
            return eVal.to(outUnit).round(2)
        else:
            raise NotImplementedError
