# Definiciones de Variables Macro (Globales)
# Estas variables se calculan internamente pero no se muestran en el CSV.
# El sistema usará el primer código/vector encontrado como "Delegado" para inyectar valores.

GLOBAL_DEFINITIONS = {
    "BGLO": "C104 + C105 + C106 + C108 + C955 + C1632 + C110 + C155 + C152 + C1032 + C1891 + C1104 + C1098 + C1030 + C159 + C748",
    "RGLO": "C169 + C166 + C907 + C1833",
    "IGLO": "C157 + C1017 + C1033 + C201 + C1035 + C910",
    "PGLO": "C1592 + C1024 + C1593 + C1025 + C1594 + C1026 + C1595 + C1027 + C603 + C1721 + C1722 + C1596 + C954 + C1597 + C1598 + C1599 + C1631 + C605 + C1633 + C1105 + C1634 + C606 + C1635 + C1031 + C1890 + C1914",
    "CGLO": "C1036 + C1101 + C135 + C136 + C176 + C752 + C608 + C1636 + C1637 + C1638 + C895 + C867 + C609 + C1639 + C1018 + C162 + C174 + C610 + C746 + C866 + C607",
    "IMP": "C31 + C20 + C1113 + C1642 + C189 + C1039 + C79 + C1041 + C1042 + C825 + C1976 + C1044 + C114 + C1830 + C1837 + C909 + C952 + C755 + C134 + C34 + C1644 + C911 + C913 + C923 + C924 + C1051 + C1052 + C21 + C43 + C767 + C862",
    "DED": "C71 + C36 + C848 + C82 + C1123 + C83 + C173 + C198 + C54 + C832 + C1907 + C833 + C1908 + C757 + C58 + C1645 + C181 + C881 + C1646 + C1647 + C1910 + C1915",
    "OTROS_CARGOS": "C900 + C1796 + C1827",
    "BAL": "C122 + C123 + C101 + C102 + C784 + C129 + C648 + C647 + C1003 + C1004 + C843",
    "CIRA": "C898 + C373 + C382 + C761 + C773 + C365 + C366 + C392 + C984 + C839 + C384 + C390 + C742 + C841 + C855 + C953",
    "VBR": "C1055 + C1056 + C1057 + C1058 + C1060 + C1061 + C1062 + C1099 + C1847 + C1100 + C1114 + C1981 + C1983 + C1985 + C1987 + C1982 + C1984 + C1986 + C1988 + C1063 + C1989 + C1990 + C1064 + C1065",
    "INTER": "C783 + C976 + C978 + C1020 + C1019 + C974",
    "OTROS": "C1005 + C975 + C1021 + C1191 + C1192 + C1193 + C1194 + C1782 + C1783",
    "SALDO": "C1195 + C1691 + C1196 + C1197 + C238 + C1586",
    "DEP": "C940 + C938 + C949 + C950 + C1066",
    "REC7": "C1358 + C1359 + C1360 + C1361 + C1184 + C1362 + C1363 + C1364 + C1096 + C1097 + C1106 + C1372",
    "REC8": "C994 + C986 + C987 + C988 + C792 + C876 + C990 + C991 + C1001 + C794 + C989 + C993 + C815 + C741 + C772 + C873 + C1120 + C1122 + C1838 + C1775 + C1911 + C1992 + C811 + C1002 + C1121 + C1124 + C1839 + C898 + C373 + C382 + C761 + C773 + C365 + C366 + C984 + C839 + C384 + C390 + C742 + C841 + C855"
}

# NUEVAS DEFINICIONES COMPLEJAS (REX y REX_2)
# Nota: Se han convertido al formato estándar SI(condición; verdadero; falso)

GLOBAL_DEFINITIONS.update({
    "REX": """
    SI(
        C104 + Vx013691 + Vx013692 + Vx013693 + Vx013694 + Vx014051 + Vx014052 + Vx014053 + 
        Vx014054 + C106 + Vx011576 + Vx011577 + Vx011578 + Vx011579 + Vx011580 + Vx011804 + 
        C108 + Vx012420 + C955 + Vx012424 + 
        C1632 + Vx013600 + C110 + Vx010381 + Vx010011 + Vx010148 + Vx010128 + 
        POS(Vx010201 - Vx010136) + Vx010382 + Vx011321 + Vx011322 + 
        C1032 + Vx013196 + Vx013197 + C1891 + C1104 > 0; 
        1; 
        0
    )
    """,

    "REX_2": """
    SI(
        C104 + Vx013691 + Vx013692 + Vx013693 + Vx013694 + Vx014051 + Vx014052 + Vx014053 + 
        Vx014054 + C106 + Vx011576 + Vx011577 + Vx011578 + Vx011579 + Vx011580 + Vx011804 + 
        C108 + Vx012420 + C955 + Vx012424 + C1632 + Vx013600 + C110 + Vx010381 + Vx010011 + 
        Vx010148 + Vx010128 + POS(Vx010201 - Vx010136) + Vx010382 + Vx011321 + Vx011322 + 
        C1032 + Vx013196 + Vx013197 + C1891 + C1104 > 0; 
        1; 
        0
    )
    """
})

# NUEVAS DEFINICIONES COMPLEJAS (RKM y RCAV)
# Nota: Se han convertido llaves {} a () y la estructura a SI(...)

GLOBAL_DEFINITIONS.update({
    "RKM": """
    SI(
        POS(
            Vx010357 + Vx010145 + Vx010059 - Vx010146 - Vx010358 - Vx010088 + 
            Vx011930 - Vx011931 + Vx012832 - Vx012833 + Vx012836 - Vx012837 + 
            Vx013663 + Vx013664 + Vx013665 + Vx013666 + Vx013675 + Vx013676 + 
            Vx013677 + Vx013678 + Vx013679 + Vx013680 + Vx013683 + Vx013684 + 
            Vx013685 + Vx013688 + Vx013719 + Vx013720 + Vx013721 + Vx013722 + 
            Vx013731 + Vx013732 + Vx013733 + Vx013734 + Vx013735 + Vx013736 + 
            Vx013739 + Vx013740 + Vx013741 + Vx013744 + Vx014062 + Vx014063 + 
            Vx014064 + Vx014065 + Vx014079 + Vx014080 + Vx014081 + Vx014082 + 
            Vx014083 + Vx014084 + Vx014087 + Vx014088 + Vx014089 + Vx014092 + 
            Vx010653 + Vx014447
        ) > P18;
        1;
        0
    )
    """,

    "RCAV": """
    SI(
        POS(Vx010055 - Vx010087) > P36;
        1;
        0
    )
    """
})