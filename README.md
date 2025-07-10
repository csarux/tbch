# tbch
-----

Un módulo python y una aplicación streamlit para transformar planes entre Varian True Beam con diferente MLC.

La aplicación permite cargar un archivo DICOM RTPlan y transformarlo a otro tipo de MLC, ya sea de tipo Millennium a HD o viceversa.

Basándose en el los límites individuales de las láminas se infiere el tipo de MLC y se transforma el plan, modificando los límites de las láminas del MLC.

En la dirección Millenium a HD, las posiciones de las láminas más estrechas se agrupan dos a dos según el plan original.

En la dirección HD a Millenium, las posiciones de las láminas más estrechas se promedian a partir de las posiciones de las láminas adyacentes.

El código es el original escrito por Juan Calama con pequeñas modificaciones de funcionalidad.