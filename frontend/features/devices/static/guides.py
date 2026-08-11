# ══════════════════════════════════════════════════════════════
# MAINTENANCE GUIDES (public)
# Content source: "Medical Equipment Maintenance Manual —
# First line maintenance for end users" — Ministry of Health and
# Family Welfare, New Delhi.
# ══════════════════════════════════════════════════════════════


GUIDES = [
    {   
        "slug": "anaesthetic_machine",
        "lang": "en",
        "title": "Anaesthetic Machines",
        "function": (
            "The anaesthetic machine (or anaesthesia machine in America) is used by "
            "anaesthesiologists and nurse anaesthetists to support the administration of "
            "anaesthesia. The most common type of anaesthetic machine is the continuous-flow "
            "anaesthetic machine, which is designed to provide an accurate and continuous supply "
            "of medical gases (such as oxygen and nitrous oxide), mixed with an accurate "
            "concentration of anaesthetic vapour (such as halothane or isoflurane), and deliver "
            "this to the patient at a safe pressure and flow. Modern machines incorporate a "
            "ventilator, suction unit, and patient monitoring devices."
        ),
        "how_it_works": (
            "Oxygen (O2), nitrous oxide (N2O) and sometimes air sources are connected to the "
            "machine. Through gas flowmeters (or rotameters), a controlled mixture of these gases "
            "along with anaesthetic vapour passes through a vaporizer and is delivered to the "
            "patient. Sometimes a ventilator is also connected with the machine for re-breathing "
            "thus making it a closed circuit. With ventilators or a re-breathing patient circuit, "
            "soda lime canisters are used to absorb the exhaled carbon dioxide and fresh gases are "
            "added to the circuit for reuse. Pressure gauges are installed on the anaesthesia "
            "machine to monitor gas pressure. Generally, 25% (or 21%) oxygen is always kept in the "
            "circuit (delivered to patient) as a safety feature. The device which ensures this "
            "minimum oxygen in the circuit is called a hypoxic guard. Some basic machines do not "
            "have this feature, but have a nitrous lock which stops the delivery of N2O in absence "
            "of O2 pressure. Machines give various alarms to alert operators."
        ),
        "faults": [
            {"fault": "Equipment is not running", "cases": [
                ("No power at mains socket", "Check power switch is on. Replace fuse with correct voltage and current rating if blown. Check mains power is present at socket using equipment known to be working. Contact electrician for rewiring if power not present."),
                ("Electrical cable fault", "Refer to electrician for repair."),
            ]},
            {"fault": "No gas output", "cases": [
                ("No O2 pressure in cylinder / gas supply.", "Restore gas supply or replace gas cylinders. Check pressure gauges for gas pressure (about 4 bar or 4 kg/cm2). Replace O2 cylinder and/or N2O cylinder in case of low pressure."),
            ]},
            {"fault": "O2 failure alarm not working", "cases": [
                ("Alarm battery is low. Alarm device is not working.", "Call biomedical technician to fix the problem."),
            ]},
            {"fault": "Machine has leaks", "cases": [
                ("Poor seal (commonly occurring around tubing connections, flow valves and O2 / N2O yokes).", "Clean leaking seal or gasket, replace if broken. If leaks remain, call technician for repair."),
                ("Cylinders not seated in yokes properly.", "Refit cylinders in yokes and retest. If leaks remain, call technician for repair."),
            ]},
            {"fault": "Flowmeter fault", "cases": [
                ("Over tightening of the needle valve or sticking of the float / ball.", "Refer to biomedical technician."),
            ]},
            {"fault": "Electrical shocks", "cases": [
                ("Wiring fault", "Refer to electrician immediately."),
            ]},
        ],
        "daily": [
            "Remove any dust / dirt with dry cloth",
            "Remove water and waste matter from inside",
            "If any leak is audible, check with soapy solution",
            "Check all seals, connectors, adapters and parts are tight",
            "Check all moving parts move freely, all holes are unblocked",
            "Report any faults to technician immediately",
            "After use, depressurize system and replace all caps / covers",
        ],
        "weekly": [
            "Clean inside and outside with damp cloth and dry off",
            "Check connections for leakage with soap solution and dry off",
            "Check all fittings for proper assembly",
            "Replace soda lime if it has turned blue",
            "Replace any deteriorated hoses and tubing",
            "If seal, plug, cable or socket are damaged, replace",
            "When next used, check pressure gauges rise",
            "When next used, check there are no leaks",
        ],
        "fr": {
            "title": "Machines d'anesthésie",
            "function": (
                "La machine d'anesthésie est utilisée par les anesthésiologistes et les infirmiers "
                "anesthésistes pour soutenir l'administration de l'anesthésie. Le type le plus "
                "courant est la machine à débit continu, conçue pour fournir un apport précis et "
                "continu de gaz médicaux (comme l'oxygène et le protoxyde d'azote), mélangé à une "
                "concentration précise de vapeur anesthésique (comme l'halothane ou l'isoflurane), "
                "et le délivrer au patient à une pression et un débit sûrs. Les machines modernes "
                "intègrent un ventilateur, une unité d'aspiration et des dispositifs de "
                "surveillance du patient."
            ),
            "how_it_works": (
                "L'oxygène (O2), le protoxyde d'azote (N2O) et parfois l'air sont raccordés à la "
                "machine. Grâce aux débitmètres de gaz (ou rotamètres), un mélange contrôlé de ces "
                "gaz ainsi que de la vapeur anesthésique passe à travers un vaporisateur et est "
                "délivré au patient. Parfois, un ventilateur est également raccordé à la machine "
                "pour permettre la re-respiration, formant ainsi un circuit fermé. Avec les "
                "ventilateurs ou un circuit de re-respiration, des cartouches de chaux sodée sont "
                "utilisées pour absorber le dioxyde de carbone expiré, et de nouveaux gaz sont "
                "ajoutés au circuit pour être réutilisés. Des manomètres sont installés sur la "
                "machine d'anesthésie pour surveiller la pression des gaz. En général, 25 % (ou "
                "21 %) d'oxygène est toujours maintenu dans le circuit (délivré au patient) comme "
                "mesure de sécurité. Le dispositif qui garantit cet oxygène minimum dans le circuit "
                "est appelé garde hypoxique. Certaines machines de base ne disposent pas de cette "
                "fonctionnalité, mais possèdent un verrou de protoxyde qui arrête l'administration "
                "de N2O en l'absence de pression d'O2. Les machines émettent diverses alarmes pour "
                "alerter les opérateurs."
            ),
            "faults": [
                {"fault": "L'équipement ne démarre pas", "cases": [
                    ("Pas de courant à la prise secteur", "Vérifiez que l'interrupteur est allumé. Remplacez le fusible par un fusible de tension et de courant corrects s'il a sauté. Vérifiez que la prise est alimentée à l'aide d'un équipement connu en état de marche. Contactez un électricien pour le câblage si le courant n'est pas présent."),
                    ("Défaut de câble électrique", "Renvoyez à l'électricien pour réparation."),
                ]},
                {"fault": "Pas de sortie de gaz", "cases": [
                    ("Pas de pression d'O2 dans la bouteille / l'alimentation en gaz.", "Rétablissez l'alimentation en gaz ou remplacez les bouteilles de gaz. Vérifiez les manomètres pour la pression du gaz (environ 4 bar ou 4 kg/cm2). Remplacez la bouteille d'O2 et/ou de N2O en cas de basse pression."),
                ]},
                {"fault": "L'alarme de panne d'O2 ne fonctionne pas", "cases": [
                    ("La batterie de l'alarme est faible. Le dispositif d'alarme ne fonctionne pas.", "Appelez un technicien biomédical pour résoudre le problème."),
                ]},
                {"fault": "La machine fuit", "cases": [
                    ("Mauvais joint (fréquent autour des raccords de tubulures, des vannes de débit et des culasses O2/N2O).", "Nettoyez le joint ou la garniture qui fuit, remplacez-les s'ils sont cassés. Si les fuites persistent, appelez un technicien pour réparation."),
                    ("Les bouteilles ne sont pas correctement logées dans les culasses.", "Replacez les bouteilles dans les culasses et retestez. Si les fuites persistent, appelez un technicien pour réparation."),
                ]},
                {"fault": "Défaut de débitmètre", "cases": [
                    ("Serrage excessif de la vanne à aiguille ou blocage du flotteur / de la bille.", "Renvoyez au technicien biomédical."),
                ]},
                {"fault": "Chocs électriques", "cases": [
                    ("Défaut de câblage", "Renvoyez immédiatement à l'électricien."),
                ]},
            ],
            "daily": [
                "Enlevez toute poussière / saleté avec un chiffon sec",
                "Enlevez l'eau et les déchets à l'intérieur",
                "Si une fuite est audible, vérifiez avec une solution savonneuse",
                "Vérifiez que tous les joints, connecteurs, adaptateurs et pièces sont bien serrés",
                "Vérifiez que toutes les pièces mobiles se déplacent librement et que tous les orifices sont dégagés",
                "Signalez toute panne au technicien immédiatement",
                "Après utilisation, dépressurisez le système et replacez tous les bouchons / couvercles",
            ],
            "weekly": [
                "Nettoyez l'intérieur et l'extérieur avec un chiffon humide et séchez",
                "Vérifiez les raccords pour détecter les fuites avec une solution savonneuse et séchez",
                "Vérifiez que toutes les fixations sont correctement assemblées",
                "Remplacez la chaux sodée si elle est devenue bleue",
                "Remplacez les tuyaux et tubulures détériorés",
                "Si le joint, la fiche, le câble ou la prise sont endommagés, remplacez-les",
                "À la prochaine utilisation, vérifiez que les manomètres montent",
                "À la prochaine utilisation, vérifiez qu'il n'y a pas de fuites",
            ],
        },
        "es": {
            "title": "Máquinas de anestesia",
            "function": (
                "La máquina de anestesia es utilizada por anestesiólogos y enfermeros anestesistas "
                "para apoyar la administración de anestesia. El tipo más común es la máquina de "
                "anestesia de flujo continuo, diseñada para proporcionar un suministro preciso y "
                "continuo de gases medicinales (como oxígeno y óxido nitroso), mezclado con una "
                "concentración precisa de vapor anestésico (como halotano o isoflurano), y "
                "administrarlo al paciente a una presión y un flujo seguros. Las máquinas modernas "
                "incorporan un ventilador, una unidad de aspiración y dispositivos de monitoreo del "
                "paciente."
            ),
            "how_it_works": (
                "El oxígeno (O2), el óxido nitroso (N2O) y a veces el aire se conectan a la "
                "máquina. A través de los medidores de flujo de gas (o rotámetros), una mezcla "
                "controlada de estos gases junto con el vapor anestésico pasa a través de un "
                "vaporizador y se administra al paciente. A veces también se conecta un ventilador "
                "a la máquina para la re-respiración, formando así un circuito cerrado. Con "
                "ventiladores o un circuito de re-respiración, se utilizan cánisters de cal sodada "
                "para absorber el dióxido de carbono exhalado, y se añaden gases frescos al circuito "
                "para su reutilización. Se instalan manómetros en la máquina de anestesia para "
                "monitorear la presión del gas. Generalmente, se mantiene siempre un 25 % (o 21 %) "
                "de oxígeno en el circuito (administrado al paciente) como medida de seguridad. El "
                "dispositivo que garantiza este oxígeno mínimo en el circuito se llama guardia "
                "hipóxica. Algunas máquinas básicas no tienen esta función, pero tienen un bloqueo "
                "de óxido nitroso que detiene la administración de N2O en ausencia de presión de O2. "
                "Las máquinas emiten diversas alarmas para alertar a los operadores."
            ),
            "faults": [
                {"fault": "El equipo no funciona", "cases": [
                    ("No hay corriente en la toma de red", "Verifica que el interruptor esté encendido. Reemplaza el fusible con la tensión y corriente correctas si se ha fundido. Comprueba que la toma tenga corriente usando un equipo que se sepa que funciona. Contacta a un electricista para el cableado si no hay corriente."),
                    ("Fallo del cable eléctrico", "Remite al electricista para su reparación."),
                ]},
                {"fault": "Sin salida de gas", "cases": [
                    ("No hay presión de O2 en el cilindro / suministro de gas.", "Restablece el suministro de gas o reemplaza los cilindros de gas. Comprueba los manómetros para la presión del gas (alrededor de 4 bar o 4 kg/cm2). Reemplaza el cilindro de O2 y/o de N2O en caso de baja presión."),
                ]},
                {"fault": "La alarma de falla de O2 no funciona", "cases": [
                    ("La batería de la alarma está baja. El dispositivo de alarma no funciona.", "Llama al técnico biomédico para solucionar el problema."),
                ]},
                {"fault": "La máquina tiene fugas", "cases": [
                    ("Sello deficiente (comúnmente alrededor de las conexiones de los tubos, las válvulas de flujo y los yugos O2/N2O).", "Limpia el sello o la junta que fuga, reemplázalo si está roto. Si las fugas persisten, llama a un técnico para su reparación."),
                    ("Los cilindros no están bien asentados en los yugos.", "Vuelve a colocar los cilindros en los yugos y vuelve a probar. Si las fugas persisten, llama a un técnico para su reparación."),
                ]},
                {"fault": "Fallo del medidor de flujo", "cases": [
                    ("Apriete excesivo de la válvula de aguja o pegado del flotador / de la bola.", "Remite al técnico biomédico."),
                ]},
                {"fault": "Descargas eléctricas", "cases": [
                    ("Fallo del cableado", "Remite inmediatamente al electricista."),
                ]},
            ],
            "daily": [
                "Elimina cualquier polvo / suciedad con un paño seco",
                "Retira el agua y los desechos del interior",
                "Si se escucha alguna fuga, compruébala con solución jabonosa",
                "Verifica que todos los sellos, conectores, adaptadores y piezas estén apretados",
                "Verifica que todas las piezas móviles se muevan libremente y que todos los orificios estén despejados",
                "Reporta cualquier falla al técnico de inmediato",
                "Después del uso, despresuriza el sistema y vuelve a colocar todas las tapas / cubiertas",
            ],
            "weekly": [
                "Limpia el interior y el exterior con un paño húmedo y seca",
                "Verifica las conexiones para detectar fugas con solución jabonosa y seca",
                "Verifica que todos los accesorios estén correctamente ensamblados",
                "Reemplaza la cal sodada si se ha vuelto azul",
                "Reemplaza las mangueras y tubos deteriorados",
                "Si el sello, enchufe, cable o toma está dañado, reemplázalo",
                "En el próximo uso, verifica que los manómetros suban",
                "En el próximo uso, verifica que no haya fugas",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "autoclave_sterilizer",
        "title": "Autoclaves and Sterilizers",
        "function": (
            "Sterilization is the killing of microorganisms that could harm patients. It can be "
            "done by heat (steam, air, flame or boiling) or by chemical means. Autoclaves use high "
            "pressure steam and sterilizers use boiling water mixed with chemicals to achieve this. "
            "Materials are placed inside the unit for a carefully specified length of time. "
            "Autoclaves achieve better sterilization than boiling water sterilizers."
        ),
        "how_it_works": (
            "Heat is delivered to water either by electricity or flame. This generates high "
            "temperature within the chamber. The autoclave also contains high pressure when in "
            "use, hence the need for pressure control valves and safety valves. Users must be "
            "careful to check how long items need to be kept at the temperature reached."
        ),
        "faults": [
            {"fault": "Equipment is not heating", "cases": [
                ("No power at mains socket", "Check power switch is on. Replace fuse with correct voltage and current rating if blown. Check mains power is present at socket using equipment known to be working. Contact electrician for rewiring if power not present."),
                ("Electrical cable fault", "Try cable on another piece of equipment. Contact electrician for repair if required."),
                ("Damaged heating element", "Replace if broken."),
            ]},
            {"fault": "Pressure rises above the marked level", "cases": [
                ("Blocked valve", "Clean the pressure regulating valve, safety valve. Pressure vessel may be over filled. Retest autoclave under pressure with water only."),
            ]},
            {"fault": "Steam is constantly escaping", "cases": [
                ("Poor seal", "Clean leaky valve and hole, replace if defective. Clean leaking seal or gasket, replace if broken."),
            ]},
            {"fault": "Electrical shocks", "cases": [
                ("Wiring fault", "Refer to electrician."),
            ]},
        ],
        "daily": [
            "Remove any dust / dirt with damp cloth and dry off",
            "Remove water and waste matter from inside",
            "Check all screws, connectors and parts are tightly fitted",
            "Check all moving parts move freely, all holes are unblocked",
            "Use troubleshooting guide if problems occur",
        ],
        "weekly": [
            "Unplug, clean inside and outside with damp cloth and dry off",
            "Check internal heating element connections are tight",
            "Replace heating element if covered with limescale",
            "If plug, cable or socket are damaged, replace",
            "When next used, check pressure / temperature gauges rise",
            "When next used, check there are no leaks",
        ],
        "fr": {
            "title": "Autoclaves et stérilisateurs",
            "function": (
                "La stérilisation consiste à tuer les micro-organismes qui pourraient nuire aux "
                "patients. Elle peut être réalisée par la chaleur (vapeur, air, flamme ou "
                "ébullition) ou par des moyens chimiques. Les autoclaves utilisent de la vapeur à "
                "haute pression et les stérilisateurs utilisent de l'eau bouillante mélangée à des "
                "produits chimiques pour y parvenir. Les matériaux sont placés à l'intérieur de "
                "l'appareil pendant une durée précisément déterminée. Les autoclaves permettent une "
                "meilleure stérilisation que les stérilisateurs à eau bouillante."
            ),
            "how_it_works": (
                "La chaleur est apportée à l'eau soit par l'électricité, soit par une flamme. Cela "
                "génère une température élevée à l'intérieur de la chambre. L'autoclave contient "
                "également une pression élevée en cours d'utilisation, d'où la nécessité de vannes "
                "de régulation de pression et de vannes de sécurité. Les utilisateurs doivent "
                "vérifier soigneusement la durée pendant laquelle les articles doivent rester à la "
                "température atteinte."
            ),
            "faults": [
                {"fault": "L'équipement ne chauffe pas", "cases": [
                    ("Pas de courant à la prise secteur", "Vérifiez que l'interrupteur est allumé. Remplacez le fusible par un fusible de tension et de courant corrects s'il a sauté. Vérifiez que la prise est alimentée à l'aide d'un équipement connu en état de marche. Contactez un électricien pour le câblage si le courant n'est pas présent."),
                    ("Défaut de câble électrique", "Essayez le câble sur un autre équipement. Contactez un électricien pour réparation si nécessaire."),
                    ("Élément chauffant endommagé", "Remplacez-le s'il est cassé."),
                ]},
                {"fault": "La pression dépasse le niveau indiqué", "cases": [
                    ("Soupape bloquée", "Nettoyez la vanne de régulation de pression et la vanne de sécurité. La cuve sous pression peut être trop remplie. Retestez l'autoclave sous pression avec de l'eau uniquement."),
                ]},
                {"fault": "La vapeur s'échappe constamment", "cases": [
                    ("Mauvais joint", "Nettoyez la vanne et l'orifice qui fuient, remplacez-les s'ils sont défectueux. Nettoyez le joint ou la garniture qui fuit, remplacez-les s'ils sont cassés."),
                ]},
                {"fault": "Chocs électriques", "cases": [
                    ("Défaut de câblage", "Renvoyez à l'électricien."),
                ]},
            ],
            "daily": [
                "Enlevez toute poussière / saleté avec un chiffon humide et séchez",
                "Enlevez l'eau et les déchets à l'intérieur",
                "Vérifiez que toutes les vis, connecteurs et pièces sont bien serrés",
                "Vérifiez que toutes les pièces mobiles se déplacent librement et que tous les orifices sont dégagés",
                "Utilisez le guide de dépannage si des problèmes surviennent",
            ],
            "weekly": [
                "Débranchez, nettoyez l'intérieur et l'extérieur avec un chiffon humide et séchez",
                "Vérifiez que les connexions de l'élément chauffant interne sont bien serrées",
                "Remplacez l'élément chauffant s'il est recouvert de tartre",
                "Si la fiche, le câble ou la prise sont endommagés, remplacez-les",
                "À la prochaine utilisation, vérifiez que les manomètres / thermomètres montent",
                "À la prochaine utilisation, vérifiez qu'il n'y a pas de fuites",
            ],
        },
        "es": {
            "title": "Autoclaves y esterilizadores",
            "function": (
                "La esterilización es la destrucción de microorganismos que podrían dañar a los "
                "pacientes. Se puede realizar mediante calor (vapor, aire, llama o ebullición) o por "
                "medios químicos. Los autoclaves utilizan vapor a alta presión y los esterilizadores "
                "utilizan agua hirviendo mezclada con productos químicos para lograrlo. Los "
                "materiales se colocan dentro de la unidad durante un período de tiempo "
                "cuidadosamente especificado. Los autoclaves logran una mejor esterilización que los "
                "esterilizadores de agua hirviendo."
            ),
            "how_it_works": (
                "El calor se entrega al agua mediante electricidad o llama. Esto genera una "
                "temperatura alta dentro de la cámara. El autoclave también contiene alta presión "
                "cuando está en uso, por lo que se necesitan válvulas de control de presión y "
                "válvulas de seguridad. Los usuarios deben tener cuidado de verificar cuánto tiempo "
                "deben permanecer los artículos a la temperatura alcanzada."
            ),
            "faults": [
                {"fault": "El equipo no calienta", "cases": [
                    ("No hay corriente en la toma de red", "Verifica que el interruptor esté encendido. Reemplaza el fusible con la tensión y corriente correctas si se ha fundido. Comprueba que la toma tenga corriente usando un equipo que se sepa que funciona. Contacta a un electricista para el cableado si no hay corriente."),
                    ("Fallo del cable eléctrico", "Prueba el cable en otro equipo. Contacta a un electricista para su reparación si es necesario."),
                    ("Elemento calefactor dañado", "Reemplázalo si está roto."),
                ]},
                {"fault": "La presión sube por encima del nivel marcado", "cases": [
                    ("Válvula obstruida", "Limpia la válvula reguladora de presión y la válvula de seguridad. El recipiente a presión puede estar demasiado lleno. Vuelve a probar el autoclave bajo presión solo con agua."),
                ]},
                {"fault": "El vapor se escapa constantemente", "cases": [
                    ("Sello deficiente", "Limpia la válvula y el orificio que fuga, reemplázalos si están defectuosos. Limpia el sello o la junta que fuga, reemplázalos si están rotos."),
                ]},
                {"fault": "Descargas eléctricas", "cases": [
                    ("Fallo del cableado", "Remite al electricista."),
                ]},
            ],
            "daily": [
                "Elimina cualquier polvo / suciedad con un paño húmedo y seca",
                "Retira el agua y los desechos del interior",
                "Verifica que todos los tornillos, conectores y piezas estén bien ajustados",
                "Verifica que todas las piezas móviles se muevan libremente y que todos los orificios estén despejados",
                "Usa la guía de solución de problemas si surgen problemas",
            ],
            "weekly": [
                "Desenchufa, limpia el interior y el exterior con un paño húmedo y seca",
                "Verifica que las conexiones del elemento calefactor interno estén apretadas",
                "Reemplaza el elemento calefactor si está cubierto de sarro",
                "Si el enchufe, cable o toma está dañado, reemplázalo",
                "En el próximo uso, verifica que los manómetros / termómetros suban",
                "En el próximo uso, verifica que no haya fugas",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "ecg_machine",
        "title": "ECG (Electrocardiograph) Machines",
        "function": (
            "ECG machines are used to monitor the electrical activity of the heart and display it "
            "on a small screen or record it on a piece of paper. The recordings are used to "
            "diagnose the condition of the heart muscle and its nerve system."
        ),
        "how_it_works": (
            "The electrical activity is picked up by means of electrodes placed on the skin. The "
            "signal is amplified, processed if necessary and then ECG tracings displayed and "
            "printed. Some ECG machines also provide preliminary interpretation of ECG recordings. "
            "There are 12 different types of recording displayed depending upon the points from "
            "where the recordings are taken. Care must be taken to make the electrode sites clean "
            "of dirt before applying electrode jelly. Most problems occur with the patient cables "
            "or electrodes."
        ),
        "faults": [
            {"fault": "ECG traces have artifacts or base line drift", "cases": [
                ("Improper grounding", "Try with battery power only. If the recording improves then problem is with grounding. Check the grounding. Power the machine from another outlet with proper electrical ground."),
            ]},
            {"fault": "ECG traces have artefacts in one or more traces, but not in all traces", "cases": [
                ("Improper electrode connection with patient or problem with the ECG cable", "Check the patient cable continuity with continuity tester. Replace cable if found faulty. Check the electrodes expiration date. Check patient skin preparation. Check limb electrodes and chest electrodes for damage, replace if necessary."),
            ]},
            {"fault": "Paper feed not advancing", "cases": [
                ("Incorrect paper loading", "Use instructions to reload paper."),
            ]},
            {"fault": "Printing not clear or not uniform", "cases": [
                ("Printing head problem", "Adjust the printing head temperature or position. Clean the printing head with head cleaner. If no improvement, replace the printing head. Check the paper roller and replace if not smooth."),
            ]},
            {"fault": "The machine shuts down after a few minutes while on battery power", "cases": [
                ("Problem with battery or charging circuit", "Recharge the unit overnight. If there is no improvement then replace the battery. If still no improvement, refer to technician."),
            ]},
        ],
        "daily": [
            "Clean off dust with dry cloth and replace dust cover",
            "Check that battery charge indicator, power indicator and patient cable connector indicators are working",
            "Check the calibration of machine before use using 1mV pulse",
            "Check the baseline of the ECG recording is steady",
            "Check the printing is clear",
        ],
        "weekly": [
            "Clean the printing head",
            "Check all cables are not bent, knotted or damaged",
            "Replace any damaged electrical plugs, sockets or cables",
            "Check all knobs, switches and indicators are tightly fitted",
            "Check the calibration of recordings with ECG simulator",
            "Check battery power can operate the equipment",
        ],
        "fr": {
            "title": "Appareils d'ECG (électrocardiographes)",
            "function": (
                "Les appareils d'ECG sont utilisés pour surveiller l'activité électrique du cœur et "
                "l'afficher sur un petit écran ou l'enregistrer sur du papier. Les enregistrements "
                "servent à diagnostiquer l'état du muscle cardiaque et de son système nerveux."
            ),
            "how_it_works": (
                "L'activité électrique est captée au moyen d'électrodes placées sur la peau. Le "
                "signal est amplifié, traité si nécessaire, puis les tracés ECG sont affichés et "
                "imprimés. Certains appareils d'ECG fournissent également une interprétation "
                "préliminaire des enregistrements. Il existe 12 types d'enregistrements différents "
                "selon les points de mesure. Il faut veiller à ce que les sites des électrodes "
                "soient exempts de saleté avant d'appliquer le gel. La plupart des problèmes "
                "surviennent au niveau des câbles patient ou des électrodes."
            ),
            "faults": [
                {"fault": "Les tracés ECG présentent des artefacts ou une dérive de la ligne de base", "cases": [
                    ("Mise à la terre inadéquate", "Essayez avec l'alimentation par batterie uniquement. Si l'enregistrement s'améliore, le problème vient de la mise à la terre. Vérifiez la mise à la terre. Alimentez la machine à partir d'une autre prise correctement mise à la terre."),
                ]},
                {"fault": "Artefacts sur une ou plusieurs voies, mais pas sur toutes", "cases": [
                    ("Mauvaise connexion des électrodes au patient ou problème du câble ECG", "Vérifiez la continuité du câble patient avec un testeur de continuité. Remplacez le câble s'il est défectueux. Vérifiez la date de péremption des électrodes. Vérifiez la préparation de la peau du patient. Vérifiez les électrodes des membres et de la poitrine pour déceler tout dommage, remplacez-les si nécessaire."),
                ]},
                {"fault": "L'avancement du papier ne se fait pas", "cases": [
                    ("Mauvais chargement du papier", "Suivez les instructions pour recharger le papier."),
                ]},
                {"fault": "Impression floue ou irrégulière", "cases": [
                    ("Problème de tête d'impression", "Réglez la température ou la position de la tête d'impression. Nettoyez la tête d'impression avec un produit de nettoyage. Si aucun progrès, remplacez la tête d'impression. Vérifiez le rouleau de papier et remplacez-le s'il n'est pas lisse."),
                ]},
                {"fault": "La machine s'éteint après quelques minutes sur batterie", "cases": [
                    ("Problème de batterie ou de circuit de charge", "Rechargez l'appareil pendant la nuit. Si aucun progrès, remplacez la batterie. Si toujours aucun progrès, renvoyez au technicien."),
                ]},
            ],
            "daily": [
                "Enlevez la poussière avec un chiffon sec et remettez la housse",
                "Vérifiez que l'indicateur de charge de la batterie, l'indicateur d'alimentation et les indicateurs du connecteur du câble patient fonctionnent",
                "Vérifiez l'étalonnage de la machine avant utilisation avec une impulsion de 1 mV",
                "Vérifiez que la ligne de base de l'enregistrement ECG est stable",
                "Vérifiez que l'impression est nette",
            ],
            "weekly": [
                "Nettoyez la tête d'impression",
                "Vérifiez que tous les câbles ne sont ni pliés, ni noués, ni endommagés",
                "Remplacez toute fiche, prise ou câble électrique endommagé",
                "Vérifiez que tous les boutons, interrupteurs et indicateurs sont bien fixés",
                "Vérifiez l'étalonnage des enregistrements avec un simulateur ECG",
                "Vérifiez que la batterie peut alimenter l'équipement",
            ],
        },
        "es": {
            "title": "Electrocardiógrafos (ECG)",
            "function": (
                "Los electrocardiógrafos se utilizan para monitorear la actividad eléctrica del "
                "corazón y mostrarla en una pequeña pantalla o registrarla en papel. Los registros "
                "se utilizan para diagnosticar el estado del músculo cardíaco y de su sistema "
                "nervioso."
            ),
            "how_it_works": (
                "La actividad eléctrica se capta mediante electrodos colocados sobre la piel. La "
                "señal se amplifica, se procesa si es necesario y luego los trazados del ECG se "
                "muestran e imprimen. Algunos electrocardiógrafos también proporcionan una "
                "interpretación preliminar de los registros. Existen 12 tipos diferentes de registros "
                "según los puntos donde se toman. Se debe tener cuidado de limpiar los sitios de los "
                "electrodos antes de aplicar el gel. La mayoría de los problemas ocurren con los "
                "cables del paciente o los electrodos."
            ),
            "faults": [
                {"fault": "Los trazados del ECG tienen artefactos o deriva de la línea de base", "cases": [
                    ("Conexión a tierra inadecuada", "Prueba solo con alimentación por batería. Si el registro mejora, el problema es la conexión a tierra. Verifica la conexión a tierra. Alimenta la máquina desde otra toma con una conexión a tierra adecuada."),
                ]},
                {"fault": "Artefactos en uno o más trazados, pero no en todos", "cases": [
                    ("Conexión inadecuada de los electrodos al paciente o problema con el cable del ECG", "Comprueba la continuidad del cable del paciente con un probador de continuidad. Reemplaza el cable si está defectuoso. Comprueba la fecha de caducidad de los electrodos. Comprueba la preparación de la piel del paciente. Revisa los electrodos de extremidades y de pecho por daños, reemplázalos si es necesario."),
                ]},
                {"fault": "El avance del papel no progresa", "cases": [
                    ("Carga incorrecta del papel", "Usa las instrucciones para recargar el papel."),
                ]},
                {"fault": "La impresión no es clara ni uniforme", "cases": [
                    ("Problema del cabezal de impresión", "Ajusta la temperatura o la posición del cabezal de impresión. Limpia el cabezal con un limpiador. Si no mejora, reemplaza el cabezal. Comprueba el rodillo del papel y reemplázalo si no está liso."),
                ]},
                {"fault": "La máquina se apaga después de unos minutos con batería", "cases": [
                    ("Problema con la batería o el circuito de carga", "Recarga la unidad durante la noche. Si no hay mejora, reemplaza la batería. Si aún no mejora, remite al técnico."),
                ]},
            ],
            "daily": [
                "Limpia el polvo con un paño seco y vuelve a colocar la funda",
                "Verifica que el indicador de carga de la batería, el indicador de encendido y los indicadores del conector del cable del paciente funcionen",
                "Verifica la calibración de la máquina antes de usarla con un pulso de 1 mV",
                "Verifica que la línea de base del registro del ECG sea estable",
                "Verifica que la impresión sea clara",
            ],
            "weekly": [
                "Limpia el cabezal de impresión",
                "Verifica que todos los cables no estén doblados, anudados o dañados",
                "Reemplaza cualquier enchufe, toma o cable eléctrico dañado",
                "Verifica que todos los botones, interruptores e indicadores estén bien ajustados",
                "Verifica la calibración de los registros con un simulador de ECG",
                "Verifica que la batería pueda alimentar el equipo",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "electronic_diagnostic_equipment",
        "title": "Electronic Diagnostic Equipment",
        "function": (
            "There are many items of equipment in a hospital that use electronics for operation. "
            "The maintenance of such equipment is a task for specialised and trained staff. "
            "However, regular inspection and cleaning will help such equipment last for a long "
            "time and deliver safe function. These are tasks that the equipment user can carry out "
            "and should be done regularly. The types of equipment that might be included in this "
            "category are for instance audiometers, blood gas analyzers, cardiac monitors, "
            "cryoprobes, infusion pumps and stimulators."
        ),
        "how_it_works": (
            "The electrical section of the machine that is most important for safety, and also is "
            "the most likely to give problems, is the power supply. The power supply converts the "
            "voltage to a lower, stable value to make the equipment work and also protects the "
            "patient from the mains voltage. Any damage to the power supply, or any liquid spilled "
            "near it, is very serious indeed. The maintenance checklist therefore majors on "
            "checking the cables, fuses and power connectors. If a device uses low voltage "
            "batteries, it is safer to use. In this case, the user should take care that the "
            "batteries are removed if the equipment will not be used for longer than one month, as "
            "chemical spillage can occur. Rechargeable batteries must be kept topped up with charge."
        ),
        "faults": [
            {"fault": "Equipment is not running", "cases": [
                ("No power from mains socket", "Check power switch is on. Replace fuse with correct voltage and current rating if blown. Check mains power is present at socket using equipment known to be working. Contact electrician for rewiring if power not present."),
                ("Electrical cable fault", "Try cable on another piece of equipment. Contact electrician for repair if required."),
            ]},
            {"fault": "Fuse keeps blowing", "cases": [
                ("Power supply or cable fault", "Refer to electrician."),
            ]},
            {"fault": "Equipment not fully operational", "cases": [
                ("Part malfunction", "Check controls for correct positioning and operation (refer to user manual). Check all bulbs, heaters and connectors for function. Repair or replace if necessary."),
            ]},
            {"fault": "Electrical shocks", "cases": [
                ("Wiring fault", "Refer to electrician."),
            ]},
        ],
        "daily": [
            "Wipe dust off exterior and cover equipment after checks",
            "Remove any tape, paper or foreign body from equipment",
            "Check all fittings and accessories are mounted correctly",
            "Check there are no cracks in covers or liquid spillages",
            "If in use that day, run a brief function check before clinic",
        ],
        "weekly": [
            "Unplug, clean outside with damp cloth and dry off",
            "Clean any filters or covers as directed by user manual",
            "Tighten any loose screws and check parts are fitted tightly",
            "Check mains plug screws are tight",
            "Check mains cable has no bare wire and is not damaged",
            "Check any paper, oil, batteries etc. required are sufficient",
            "Check all switches operate correctly",
        ],
        "fr": {
            "title": "Équipement de diagnostic électronique",
            "function": (
                "De nombreux équipements d'un hôpital utilisent l'électronique pour fonctionner. "
                "La maintenance de ces équipements relève du personnel spécialisé et formé. "
                "Cependant, une inspection et un nettoyage réguliers aideront ces équipements à "
                "durer longtemps et à fonctionner en toute sécurité. Ce sont des tâches que "
                "l'utilisateur de l'équipement peut effectuer et qui doivent être faites "
                "régulièrement. Les équipements pouvant être inclus dans cette catégorie sont par "
                "exemple les audiomètres, les analyseurs de gaz du sang, les moniteurs cardiaques, "
                "les cryosondes, les pompes à perfusion et les stimulateurs."
            ),
            "how_it_works": (
                "La section électrique de la machine la plus importante pour la sécurité, et aussi "
                "la plus susceptible de poser problème, est l'alimentation électrique. Elle convertit "
                "la tension en une valeur plus basse et stable pour faire fonctionner l'équipement "
                "et protège également le patient de la tension secteur. Tout dommage à "
                "l'alimentation, ou tout liquide renversé à proximité, est très grave. La liste de "
                "contrôle met donc l'accent sur la vérification des câbles, des fusibles et des "
                "connecteurs d'alimentation. Si un appareil utilise des piles basse tension, il est "
                "plus sûr à utiliser. Dans ce cas, l'utilisateur doit veiller à retirer les piles si "
                "l'équipement ne sera pas utilisé pendant plus d'un mois, car un écoulement "
                "chimique peut survenir. Les piles rechargeables doivent être maintenues chargées."
            ),
            "faults": [
                {"fault": "L'équipement ne fonctionne pas", "cases": [
                    ("Pas de courant à la prise secteur", "Vérifiez que l'interrupteur est allumé. Remplacez le fusible par un fusible de tension et de courant corrects s'il a sauté. Vérifiez que la prise est alimentée à l'aide d'un équipement connu en état de marche. Contactez un électricien pour le câblage si le courant n'est pas présent."),
                    ("Défaut de câble électrique", "Essayez le câble sur un autre équipement. Contactez un électricien pour réparation si nécessaire."),
                ]},
                {"fault": "Le fusible saute sans cesse", "cases": [
                    ("Défaut d'alimentation ou de câble", "Renvoyez à l'électricien."),
                ]},
                {"fault": "L'équipement n'est pas pleinement opérationnel", "cases": [
                    ("Dysfonctionnement d'une pièce", "Vérifiez la position et le fonctionnement corrects des commandes (reportez-vous au manuel d'utilisation). Vérifiez le fonctionnement de toutes les ampoules, résistances et connecteurs. Réparez ou remplacez si nécessaire."),
                ]},
                {"fault": "Chocs électriques", "cases": [
                    ("Défaut de câblage", "Renvoyez à l'électricien."),
                ]},
            ],
            "daily": [
                "Essuyez la poussière de l'extérieur et recouvrez l'équipement après les vérifications",
                "Retirez tout ruban adhésif, papier ou corps étranger de l'équipement",
                "Vérifiez que toutes les fixations et accessoires sont correctement montés",
                "Vérifiez qu'il n'y a ni fissure dans les capots ni déversement de liquide",
                "S'il est utilisé ce jour-là, effectuez un bref contrôle de fonctionnement avant la consultation",
            ],
            "weekly": [
                "Débranchez, nettoyez l'extérieur avec un chiffon humide et séchez",
                "Nettoyez les filtres ou capots conformément au manuel d'utilisation",
                "Resserrez les vis desserrées et vérifiez que les pièces sont bien fixées",
                "Vérifiez que les vis de la prise secteur sont bien serrées",
                "Vérifiez que le câble secteur ne présente ni fil dénudé ni dommage",
                "Vérifiez que le papier, l'huile, les piles, etc. nécessaires sont en quantité suffisante",
                "Vérifiez que tous les interrupteurs fonctionnent correctement",
            ],
        },
        "es": {
            "title": "Equipo de diagnóstico electrónico",
            "function": (
                "Hay muchos equipos en un hospital que utilizan electrónica para su funcionamiento. "
                "El mantenimiento de tales equipos es una tarea para personal especializado y "
                "capacitado. Sin embargo, la inspección y limpieza regulares ayudarán a que estos "
                "equipos duren mucho tiempo y funcionen con seguridad. Estas son tareas que el "
                "usuario del equipo puede realizar y deben hacerse con regularidad. Los tipos de "
                "equipo que podrían incluirse en esta categoría son, por ejemplo, audiómetros, "
                "analizadores de gases en sangre, monitores cardíacos, criosondas, bombas de "
                "infusión y estimuladores."
            ),
            "how_it_works": (
                "La sección eléctrica de la máquina más importante para la seguridad, y también la "
                "que tiene más probabilidades de dar problemas, es la fuente de alimentación. La "
                "fuente de alimentación convierte el voltaje a un valor más bajo y estable para que "
                "el equipo funcione y también protege al paciente del voltaje de la red. Cualquier "
                "daño a la fuente de alimentación, o cualquier líquido derramado cerca de ella, es "
                "muy grave. Por lo tanto, la lista de verificación de mantenimiento se centra en "
                "revisar los cables, fusibles y conectores de alimentación. Si un dispositivo usa "
                "baterías de bajo voltaje, es más seguro de usar. En este caso, el usuario debe "
                "tener cuidado de retirar las baterías si el equipo no se usará por más de un mes, "
                "ya que puede ocurrir derrame químico. Las baterías recargables deben mantenerse "
                "con carga."
            ),
            "faults": [
                {"fault": "El equipo no funciona", "cases": [
                    ("No hay corriente en la toma de red", "Verifica que el interruptor esté encendido. Reemplaza el fusible con la tensión y corriente correctas si se ha fundido. Comprueba que la toma tenga corriente usando un equipo que se sepa que funciona. Contacta a un electricista para el cableado si no hay corriente."),
                    ("Fallo del cable eléctrico", "Prueba el cable en otro equipo. Contacta a un electricista para su reparación si es necesario."),
                ]},
                {"fault": "El fusible se funde constantemente", "cases": [
                    ("Fallo de la fuente de alimentación o del cable", "Remite al electricista."),
                ]},
                {"fault": "El equipo no está totalmente operativo", "cases": [
                    ("Mal funcionamiento de una pieza", "Verifica la posición y el funcionamiento correctos de los controles (consulta el manual del usuario). Comprueba el funcionamiento de todas las bombillas, calentadores y conectores. Repara o reemplaza si es necesario."),
                ]},
                {"fault": "Descargas eléctricas", "cases": [
                    ("Fallo del cableado", "Remite al electricista."),
                ]},
            ],
            "daily": [
                "Limpia el polvo del exterior y cubre el equipo después de las verificaciones",
                "Retira cualquier cinta, papel o cuerpo extraño del equipo",
                "Verifica que todos los accesorios y accesorios estén montados correctamente",
                "Verifica que no haya grietas en las cubiertas ni derrames de líquidos",
                "Si se usa ese día, realiza una breve comprobación de funcionamiento antes de la consulta",
            ],
            "weekly": [
                "Desenchufa, limpia el exterior con un paño húmedo y seca",
                "Limpia los filtros o cubiertas según el manual del usuario",
                "Aprieta los tornillos sueltos y verifica que las piezas estén bien ajustadas",
                "Verifica que los tornillos del enchufe de red estén apretados",
                "Verifica que el cable de red no tenga cables pelados ni esté dañado",
                "Verifica que el papel, aceite, baterías, etc. necesarios sean suficientes",
                "Verifica que todos los interruptores funcionen correctamente",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "electrosurgical_unit",
        "title": "Electrosurgical Units (ESU) and Cautery Machines",
        "function": (
            "Electrosurgery is the application of a high-frequency electric current to biological "
            "tissue as a means to cut, coagulate, desiccate, or fulgurate tissue. Its benefits "
            "include the ability to make precise cuts with limited blood loss in hospital "
            "operating rooms or in outpatient procedures. Cautery, or electrocautery, is the "
            "application of heat to tissue to achieve coagulation."
        ),
        "how_it_works": (
            "In electrosurgical procedures, the tissue is heated by an alternating electric "
            "current being passed through it from a probe. Electrocautery uses heat conduction "
            "from an electrically heated probe, much like a soldering iron. Electrosurgery is "
            "performed using an electrosurgical generator (also referred to as power supply or "
            "waveform generator) and a hand piece including one or several electrodes, sometimes "
            "referred to as an RF Knife, or informally by surgeons as a \u201cBovie knife\u201d "
            "after the inventor. Bipolar electrosurgery has the outward and return current passing "
            "through the handpiece, whereas monopolar electrosurgery returns the current through a "
            "plate normally under the patient."
        ),
        "faults": [
            {"fault": "Equipment is not turning on", "cases": [
                ("No power from mains socket", "Check power switch is on. Replace fuse with correct voltage and current if blown. Check mains power is present at socket using equipment known to be working. Contact electrician for rewiring if power not present."),
                ("Electrical cable fault", "Try cable on another piece of equipment. Contact electrician for repair if required."),
            ]},
            {"fault": "Equipment is on but shows error signal", "cases": [
                ("Footswitch pedal may have been depressed as unit is turned on or front panel buttons may be stuck.", "Note error code and turn unit off. Check footswitch and front panel buttons. Disconnect all foot pedals. Turn on unit again."),
                ("Probe, patient cable or plate malfunction", "Check connections and plugs on all cables are tight."),
                ("Possible internal malfunction", "Call biomed technicians."),
            ]},
            {"fault": "Equipment is on but output is absent, weak or intermittent", "cases": [
                ("Power setting is too low", "Adjust power, check manual."),
                ("Malfunctioning accessory", "Check connection or replace item."),
                ("Incomplete or incorrect connection", "Check correct probe / footswitch cord are well connected."),
                ("Possible internal malfunction", "Call biomedical technician."),
            ]},
            {"fault": "Continuous interference with monitors", "cases": [
                ("Faulty ground connection", "Check all monitors and power connections. Use separate outlets for each medical device."),
                ("Poor filtering systems in monitoring equipment", "Replace monitoring device."),
            ]},
            {"fault": "Monitor interference occurs only when electrosurgery is activated", "cases": [
                ("Metal-to-metal sparking", "Check all connections are tight."),
                ("Cords and cables are bundled, touching or damaged", "Remove cable cluttering, replace damaged cords."),
                ("High power setting", "Reduce power setting, use blend mode."),
                ("Continued interference", "Contact biomedical technician."),
            ]},
            {"fault": "Pacemaker or internal cardiac defibrillator interference", "cases": [
                ("Equipment activation is causing battery or implant malfunction", "Stop procedure immediately, perform emergency care and call implant supplier before restarting procedure."),
            ]},
            {"fault": "Electrical shocks to user", "cases": [
                ("Wiring fault", "Refer to electrician."),
            ]},
        ],
        "daily": [
            "Remove any dust / dirt and replace equipment cover",
            "Remove any tape, paper or foreign body from equipment",
            "Check all fittings and cables are properly connected",
            "Check there are no signs of spilled liquids or cable damage",
            "Check foot / probe switch smooth operation.",
            "Check return plate cable disconnection alarm before use.",
        ],
        "weekly": [
            "Unplug, clean outside with damp cloth and dry off",
            "Inspect filters, clean or replace if needed.",
            "If any plug, cable or socket is damaged, replace",
            "Check proper operation of all controls, indicators and visual displays on the unit.",
            "If not recently used, check operation on wet soap",
        ],
        "fr": {
            "title": "Unités d'électrochirurgie (ESU) et cautérisateurs",
            "function": (
                "L'électrochirurgie est l'application d'un courant électrique à haute fréquence au "
                "tissu biologique pour couper, coaguler, dessécher ou fulgurer le tissu. Ses "
                "avantages incluent la capacité de réaliser des coupes précises avec une perte de "
                "sang limitée dans les salles d'opération ou lors des procédures ambulatoires. La "
                "cautérisation, ou électrocautérisation, est l'application de chaleur au tissu pour "
                "obtenir une coagulation."
            ),
            "how_it_works": (
                "Lors des procédures électrochirurgicales, le tissu est chauffé par un courant "
                "électrique alternatif qui le traverse depuis une sonde. L'électrocautérisation "
                "utilise la conduction thermique d'une sonde chauffée électriquement, un peu comme "
                "un fer à souder. L'électrochirurgie est réalisée à l'aide d'un générateur "
                "électrochirurgical (également appelé alimentation ou générateur de formes d'onde) "
                "et d'une pièce à main comprenant une ou plusieurs électrodes, parfois appelée "
                "couteau RF, ou familièrement par les chirurgiens « bistouri Bovie » d'après "
                "l'inventeur. L'électrochirurgie bipolaire fait passer le courant aller et retour à "
                "travers la pièce à main, tandis que l'électrochirurgie monopolaire fait revenir le "
                "courant par une plaque généralement placée sous le patient."
            ),
            "faults": [
                {"fault": "L'équipement ne s'allume pas", "cases": [
                    ("Pas de courant à la prise secteur", "Vérifiez que l'interrupteur est allumé. Remplacez le fusible par un fusible de tension et de courant corrects s'il a sauté. Vérifiez que la prise est alimentée à l'aide d'un équipement connu en état de marche. Contactez un électricien pour le câblage si le courant n'est pas présent."),
                    ("Défaut de câble électrique", "Essayez le câble sur un autre équipement. Contactez un électricien pour réparation si nécessaire."),
                ]},
                {"fault": "L'équipement est allumé mais affiche un signal d'erreur", "cases": [
                    ("La pédale peut avoir été enfoncée à la mise sous tension ou les boutons du panneau avant peuvent être bloqués.", "Notez le code d'erreur et éteignez l'appareil. Vérifiez la pédale et les boutons du panneau avant. Déconnectez toutes les pédales. Rallumez l'appareil."),
                    ("Dysfonctionnement de la sonde, du câble patient ou de la plaque", "Vérifiez que les connexions et fiches de tous les câbles sont bien serrées."),
                    ("Possible dysfonctionnement interne", "Appelez les techniciens biomédicaux."),
                ]},
                {"fault": "L'équipement est allumé mais la sortie est absente, faible ou intermittente", "cases": [
                    ("Puissance réglée trop bas", "Réglez la puissance, consultez le manuel."),
                    ("Accessoire défectueux", "Vérifiez la connexion ou remplacez l'article."),
                    ("Connexion incomplète ou incorrecte", "Vérifiez que la sonde / le cordon de pédale correct est bien connecté."),
                    ("Possible dysfonctionnement interne", "Appelez un technicien biomédical."),
                ]},
                {"fault": "Interférence continue avec les moniteurs", "cases": [
                    ("Connexion de masse défectueuse", "Vérifiez tous les moniteurs et connexions d'alimentation. Utilisez des prises séparées pour chaque appareil médical."),
                    ("Mauvais systèmes de filtrage de l'équipement de surveillance", "Remplacez l'appareil de surveillance."),
                ]},
                {"fault": "L'interférence du moniteur ne survient que lorsque l'électrochirurgie est activée", "cases": [
                    ("Étincelles métal contre métal", "Vérifiez que toutes les connexions sont serrées."),
                    ("Câbles regroupés, en contact ou endommagés", "Éliminez l'encombrement des câbles, remplacez les cordons endommagés."),
                    ("Réglage de puissance élevé", "Réduisez la puissance, utilisez le mode mixte."),
                    ("Interférence persistante", "Contactez un technicien biomédical."),
                ]},
                {"fault": "Interférence avec le stimulateur cardiaque ou le défibrillateur interne", "cases": [
                    ("L'activation de l'équipement provoque un dysfonctionnement de la batterie ou de l'implant", "Arrêtez immédiatement la procédure, prodiguez les soins d'urgence et appelez le fournisseur de l'implant avant de redémarrer."),
                ]},
                {"fault": "Chocs électriques à l'utilisateur", "cases": [
                    ("Défaut de câblage", "Renvoyez à l'électricien."),
                ]},
            ],
            "daily": [
                "Enlevez toute poussière / saleté et remettez le capot de l'équipement",
                "Retirez tout ruban adhésif, papier ou corps étranger de l'équipement",
                "Vérifiez que toutes les fixations et câbles sont correctement connectés",
                "Vérifiez qu'il n'y a aucun signe de liquide renversé ni de câble endommagé",
                "Vérifiez le fonctionnement souple de l'interrupteur à pied / de la sonde.",
                "Vérifiez l'alarme de déconnexion du câble de la plaque de retour avant utilisation.",
            ],
            "weekly": [
                "Débranchez, nettoyez l'extérieur avec un chiffon humide et séchez",
                "Inspectez les filtres, nettoyez-les ou remplacez-les si nécessaire.",
                "Si une fiche, un câble ou une prise est endommagé, remplacez-le",
                "Vérifiez le bon fonctionnement de toutes les commandes, indicateurs et affichages de l'appareil.",
                "S'il n'a pas été utilisé récemment, vérifiez son fonctionnement sur du savon humide",
            ],
        },
        "es": {
            "title": "Unidades electroquirúrgicas (ESU) y máquinas de cauterización",
            "function": (
                "La electrocirugía es la aplicación de una corriente eléctrica de alta frecuencia al "
                "tejido biológico como medio para cortar, coagular, desecar o fulgurar el tejido. "
                "Sus beneficios incluyen la capacidad de realizar cortes precisos con pérdida de "
                "sangre limitada en los quirófanos del hospital o en procedimientos ambulatorios. La "
                "cauterización, o electrocauterización, es la aplicación de calor al tejido para "
                "lograr la coagulación."
            ),
            "how_it_works": (
                "En los procedimientos electroquirúrgicos, el tejido se calienta mediante una "
                "corriente eléctrica alterna que lo atraviesa desde una sonda. La electrocauterización "
                "utiliza la conducción de calor de una sonda calentada eléctricamente, muy parecida a "
                "un cautín. La electrocirugía se realiza con un generador electroquirúrgico (también "
                "llamado fuente de alimentación o generador de formas de onda) y una pieza de mano "
                "que incluye uno o varios electrodos, a veces llamada bisturí de RF o, informalmente, "
                "«bisturí Bovie» por su inventor. La electrocirugía bipolar hace pasar la corriente "
                "de ida y de retorno a través de la pieza de mano, mientras que la electrocirugía "
                "monopolar devuelve la corriente a través de una placa normalmente colocada debajo "
                "del paciente."
            ),
            "faults": [
                {"fault": "El equipo no enciende", "cases": [
                    ("No hay corriente en la toma de red", "Verifica que el interruptor esté encendido. Reemplaza el fusible con la tensión y corriente correctas si se ha fundido. Comprueba que la toma tenga corriente usando un equipo que se sepa que funciona. Contacta a un electricista para el cableado si no hay corriente."),
                    ("Fallo del cable eléctrico", "Prueba el cable en otro equipo. Contacta a un electricista para su reparación si es necesario."),
                ]},
                {"fault": "El equipo está encendido pero muestra señal de error", "cases": [
                    ("El pedal del interruptor pudo haber sido presionado al encender la unidad o los botones del panel frontal pueden estar atascados.", "Anota el código de error y apaga la unidad. Revisa el pedal y los botones del panel frontal. Desconecta todos los pedales. Enciende la unidad nuevamente."),
                    ("Mal funcionamiento de la sonda, del cable del paciente o de la placa", "Verifica que las conexiones y enchufes de todos los cables estén apretados."),
                    ("Posible mal funcionamiento interno", "Llama a los técnicos biomédicos."),
                ]},
                {"fault": "El equipo está encendido pero la salida es ausente, débil o intermitente", "cases": [
                    ("La configuración de potencia es demasiado baja", "Ajusta la potencia, consulta el manual."),
                    ("Accesorio con mal funcionamiento", "Verifica la conexión o reemplaza el artículo."),
                    ("Conexión incompleta o incorrecta", "Verifica que la sonda / el cable del pedal correcto estén bien conectados."),
                    ("Posible mal funcionamiento interno", "Llama al técnico biomédico."),
                ]},
                {"fault": "Interferencia continua con los monitores", "cases": [
                    ("Conexión a tierra defectuosa", "Revisa todos los monitores y las conexiones de alimentación. Usa tomas separadas para cada dispositivo médico."),
                    ("Sistemas de filtrado deficientes en el equipo de monitoreo", "Reemplaza el dispositivo de monitoreo."),
                ]},
                {"fault": "La interferencia del monitor ocurre solo cuando se activa la electrocirugía", "cases": [
                    ("Chispas de metal a metal", "Verifica que todas las conexiones estén apretadas."),
                    ("Los cables están agrupados, en contacto o dañados", "Elimina el desorden de cables, reemplaza los cables dañados."),
                    ("Configuración de potencia alta", "Reduce la configuración de potencia, usa el modo mezcla."),
                    ("Interferencia continua", "Contacta al técnico biomédico."),
                ]},
                {"fault": "Interferencia con marcapasos o desfibrilador cardíaco interno", "cases": [
                    ("La activación del equipo está causando mal funcionamiento de la batería o del implante", "Detén el procedimiento de inmediato, realiza los cuidados de emergencia y llama al proveedor del implante antes de reiniciar."),
                ]},
                {"fault": "Descargas eléctricas al usuario", "cases": [
                    ("Fallo del cableado", "Remite al electricista."),
                ]},
            ],
            "daily": [
                "Elimina cualquier polvo / suciedad y vuelve a colocar la cubierta del equipo",
                "Retira cualquier cinta, papel o cuerpo extraño del equipo",
                "Verifica que todos los accesorios y cables estén correctamente conectados",
                "Verifica que no haya signos de líquidos derramados ni daños en los cables",
                "Verifica el funcionamiento suave del interruptor de pie / de la sonda.",
                "Verifica la alarma de desconexión del cable de la placa de retorno antes del uso.",
            ],
            "weekly": [
                "Desenchufa, limpia el exterior con un paño húmedo y seca",
                "Inspecciona los filtros, límpialos o reemplázalos si es necesario.",
                "Si algún enchufe, cable o toma está dañado, reemplázalo",
                "Verifica el funcionamiento correcto de todos los controles, indicadores y pantallas de la unidad.",
                "Si no se ha usado recientemente, verifica su funcionamiento sobre jabón húmedo",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "endoscope",
        "title": "Endoscopes",
        "function": (
            "Endoscopy means looking inside the body using an endoscope, an instrument used to "
            "examine the interior of a hollow organ or cavity of the body. Endoscopes are inserted "
            "directly into the organ. An endoscope can consist of a rigid or flexible tube, a light "
            "delivery system (light source), an optical fibre system, a lens system transmitting "
            "the image to the viewer, an eyepiece and often an additional channel to allow entry "
            "of medical instruments, fluids or manipulators. There are many different types of "
            "endoscopy, including arthroscopy, bronchoscopy, colonoscopy, colposcopy, cystoscopy, "
            "laparoscopy and laryngoscopy."
        ),
        "how_it_works": (
            "Endoscopes may be rigid or flexible, although most endoscopes in routine use are "
            "flexible. Both use lenses, tubes and light to magnify and view the internal "
            "structures of the body. Water and air, as well as surgical instruments that may be "
            "necessary to take a tissue sample, can also be passed along the hollow centre of the "
            "endoscope. The view can be recorded by a camera and displayed on a computer screen. "
            "Rigid endoscopes are usually much shorter than flexible endoscopes. They are often "
            "used to look at the surface of internal organs, and may be inserted through a small "
            "cut in the skin or a natural orifice. Gas or fluid is sometimes used to move the "
            "surface tissues of organs in order to see them more clearly. Rigid endoscopes are "
            "commonly used to examine the joints and bladder."
        ),
        "faults": [
            {"fault": "No fluid flow or suction through scope", "cases": [
                ("Blocked air / water nozzle", "Press fluid valve and flush. Clean and lubricate valve (see user manual). Check tubes are not kinked."),
                ("Loose or damage setscrew", "Refer to biomedical technician."),
            ]},
            {"fault": "Leakage in flexible endoscope", "cases": [
                ("Tears or cut in flexible shaft", "Refer to biomedical technician."),
            ]},
            {"fault": "Fluid invasion (image stains, foggy images, electrical malfunction)", "cases": [
                ("Water or other fluids in dry parts of flexible scope due to holes, tears or improper cleaning.", "Perform leak test after every procedure. If any fluid invasion occurs, refer to biomedical technician."),
            ]},
            {"fault": "Picture is cloudy or with dark spots", "cases": [
                ("Build up of matter on the distal lens.", "Clean the lens with an alcohol wipe."),
                ("Broken fibres in cable", "If these significantly affect use, return to manufacturer."),
            ]},
            {"fault": "Cannot freely bend to the degree specified", "cases": [
                ("Over-bending portion of scope.", "Do not force bending."),
                ("Fluid invasion", "Refer to biomedical technician."),
            ]},
            {"fault": "Instruments do not pass easily through the biopsy / access channel", "cases": [
                ("Damaged forceps and brushes", "Flush channel through. Check for burrs and nicks by rubbing a gloved hand over all surfaces of the accessory. Refer to biomedical technician if problem remains."),
            ]},
            {"fault": "Light not functioning", "cases": [
                ("Bulb blown", "Replace bulb with correct type."),
                ("Fuse blown", "Replace fuse with correct rating."),
                ("No power from socket", "Check power switch is on. Check mains power is present at socket using equipment known to be working. Contact electrician for rewiring if power not present."),
            ]},
            {"fault": "Electrical shocks", "cases": [
                ("Wiring fault", "Refer to electrician."),
            ]},
        ],
        "daily": [
            "Flush, rinse, dry and disinfect endoscope after every use",
            "Remove any tape, paper or foreign body from equipment",
            "Check all accessories and fittings are properly connected.",
            "Check there are no signs of damage to the flexible tube",
            "Store in correct packaging for protection",
            "Check operation of controls and tubes before use",
        ],
        "weekly": [
            "Flush, rinse, dry and disinfect endoscope",
            "Perform leak test as per manufacturer's guidelines, making sure water resistant cap is in place",
            "Unplug light source, clean with damp cloth and dry off",
            "Inspect optics for cloudiness, foreign bodies or dark spots",
            "Check sturdiness of trolley if used",
            "If any plug, cable or socket is damaged, replace",
            "Check proper operation of all controls, indicators and lamps",
        ],
        "fr": {
            "title": "Endoscopes",
            "function": (
                "L'endoscopie consiste à regarder à l'intérieur du corps à l'aide d'un endoscope, "
                "un instrument utilisé pour examiner l'intérieur d'un organe creux ou d'une cavité "
                "du corps. Les endoscopes sont insérés directement dans l'organe. Un endoscope peut "
                "se composer d'un tube rigide ou flexible, d'un système de transmission de la "
                "lumière (source lumineuse), d'un système de fibres optiques, d'un système de "
                "lentilles transmettant l'image à l'observateur, d'un oculaire et souvent d'un "
                "canal supplémentaire permettant le passage d'instruments médicaux, de liquides ou "
                "de manipulateurs. Il existe de nombreux types d'endoscopie, notamment l'arthroscopie, "
                "la bronchoscopie, la coloscopie, la colposcopie, la cystoscopie, la laparoscopie "
                "et la laryngoscopie."
            ),
            "how_it_works": (
                "Les endoscopes peuvent être rigides ou flexibles, bien que la plupart des "
                "endoscopes en usage courant soient flexibles. Les deux utilisent des lentilles, des "
                "tubes et de la lumière pour agrandir et visualiser les structures internes du corps. "
                "De l'eau et de l'air, ainsi que des instruments chirurgicaux pouvant être "
                "nécessaires pour prélever un échantillon de tissu, peuvent également passer par le "
                "centre creux de l'endoscope. L'image peut être enregistrée par une caméra et "
                "affichée sur un écran d'ordinateur. Les endoscopes rigides sont généralement "
                "beaucoup plus courts que les endoscopes flexibles. Ils sont souvent utilisés pour "
                "examiner la surface des organes internes et peuvent être insérés par une petite "
                "incision dans la peau ou un orifice naturel. Du gaz ou du liquide est parfois utilisé "
                "pour écarter les tissus de surface des organes afin de les voir plus clairement. Les "
                "endoscopes rigides sont couramment utilisés pour examiner les articulations et la "
                "vessie."
            ),
            "faults": [
                {"fault": "Pas de flux de liquide ni d'aspiration à travers l'endoscope", "cases": [
                    ("Buse air / eau bloquée", "Appuyez sur la vanne de liquide et rincez. Nettoyez et lubrifiez la vanne (voir manuel d'utilisation). Vérifiez que les tubes ne sont pas pliés."),
                    ("Vis de réglage desserrée ou endommagée", "Renvoyez au technicien biomédical."),
                ]},
                {"fault": "Fuite dans l'endoscope flexible", "cases": [
                    ("Déchirures ou coupures dans la gaine flexible", "Renvoyez au technicien biomédical."),
                ]},
                {"fault": "Invasion de liquide (taches d'image, images embuées, dysfonctionnement électrique)", "cases": [
                    ("Eau ou autres liquides dans les parties sèches de l'endoscope flexible en raison de trous, déchirures ou nettoyage inapproprié.", "Effectuez un test d'étanchéité après chaque procédure. En cas d'invasion de liquide, renvoyez au technicien biomédical."),
                ]},
                {"fault": "Image trouble ou avec des points sombres", "cases": [
                    ("Accumulation de matière sur la lentille distale.", "Nettoyez la lentille avec un linge imbibé d'alcool."),
                    ("Fibres cassées dans le câble", "Si cela affecte significativement l'utilisation, renvoyez au fabricant."),
                ]},
                {"fault": "Impossible de plier librement au degré spécifié", "cases": [
                    ("Partie de l'endoscope trop pliée.", "Ne forcez pas la courbure."),
                    ("Invasion de liquide", "Renvoyez au technicien biomédical."),
                ]},
                {"fault": "Les instruments ne passent pas facilement dans le canal de biopsie / d'accès", "cases": [
                    ("Pinces et brosses endommagées", "Rincez le canal. Recherchez les bavures et entailles en passant une main gantée sur toutes les surfaces de l'accessoire. Renvoyez au technicien biomédical si le problème persiste."),
                ]},
                {"fault": "La lumière ne fonctionne pas", "cases": [
                    ("Ampoule grillée", "Remplacez l'ampoule par le type correct."),
                    ("Fusible grillé", "Remplacez le fusible par le calibre correct."),
                    ("Pas de courant à la prise", "Vérifiez que l'interrupteur est allumé. Vérifiez que la prise est alimentée à l'aide d'un équipement connu en état de marche. Contactez un électricien pour le câblage si le courant n'est pas présent."),
                ]},
                {"fault": "Chocs électriques", "cases": [
                    ("Défaut de câblage", "Renvoyez à l'électricien."),
                ]},
            ],
            "daily": [
                "Rincez, lavez, séchez et désinfectez l'endoscope après chaque utilisation",
                "Retirez tout ruban adhésif, papier ou corps étranger de l'équipement",
                "Vérifiez que tous les accessoires et fixations sont correctement connectés.",
                "Vérifiez qu'il n'y a aucun signe de dommage au tube flexible",
                "Rangez-le dans un emballage approprié pour le protéger",
                "Vérifiez le fonctionnement des commandes et des tubes avant utilisation",
            ],
            "weekly": [
                "Rincez, lavez, séchez et désinfectez l'endoscope",
                "Effectuez un test d'étanchéité selon les directives du fabricant, en veillant à ce que le capuchon étanche soit en place",
                "Débranchez la source lumineuse, nettoyez-la avec un chiffon humide et séchez",
                "Inspectez l'optique pour détecter toute opacité, corps étranger ou point sombre",
                "Vérifiez la solidité du chariot s'il est utilisé",
                "Si une fiche, un câble ou une prise est endommagé, remplacez-le",
                "Vérifiez le bon fonctionnement de toutes les commandes, indicateurs et lampes",
            ],
        },
        "es": {
            "title": "Endoscopios",
            "function": (
                "La endoscopia significa mirar dentro del cuerpo mediante un endoscopio, un "
                "instrumento utilizado para examinar el interior de un órgano hueco o de una "
                "cavidad del cuerpo. Los endoscopios se insertan directamente en el órgano. Un "
                "endoscopio puede consistir en un tubo rígido o flexible, un sistema de transmisión "
                "de luz (fuente de luz), un sistema de fibra óptica, un sistema de lentes que "
                "transmite la imagen al espectador, un ocular y a menudo un canal adicional para "
                "permitir la entrada de instrumentos médicos, fluidos o manipuladores. Existen "
                "muchos tipos de endoscopia, incluyendo artroscopia, broncoscopia, colonoscopia, "
                "colposcopia, cistoscopia, laparoscopia y laringoscopia."
            ),
            "how_it_works": (
                "Los endoscopios pueden ser rígidos o flexibles, aunque la mayoría de los "
                "endoscopios de uso rutinario son flexibles. Ambos utilizan lentes, tubos y luz "
                "para ampliar y ver las estructuras internas del cuerpo. El agua y el aire, así como "
                "los instrumentos quirúrgicos que puedan ser necesarios para tomar una muestra de "
                "tejido, también pueden pasar a lo largo del centro hueco del endoscopio. La imagen "
                "puede registrarse con una cámara y mostrarse en una pantalla de computadora. Los "
                "endoscopios rígidos suelen ser mucho más cortos que los flexibles. A menudo se usan "
                "para observar la superficie de los órganos internos y pueden insertarse a través de "
                "una pequeña incisión en la piel o un orificio natural. A veces se usa gas o líquido "
                "para mover los tejidos superficiales de los órganos y verlos con mayor claridad. "
                "Los endoscopios rígidos se usan comúnmente para examinar las articulaciones y la "
                "vejiga."
            ),
            "faults": [
                {"fault": "Sin flujo de líquido ni succión a través del endoscopio", "cases": [
                    ("Boquilla de aire / agua obstruida", "Presiona la válvula de líquido y enjuaga. Limpia y lubrica la válvula (consulta el manual del usuario). Verifica que los tubos no estén doblados."),
                    ("Tornillo de ajuste flojo o dañado", "Remite al técnico biomédico."),
                ]},
                {"fault": "Fuga en el endoscopio flexible", "cases": [
                    ("Desgarros o cortes en el eje flexible", "Remite al técnico biomédico."),
                ]},
                {"fault": "Invasión de líquido (manchas en la imagen, imágenes borrosas, mal funcionamiento eléctrico)", "cases": [
                    ("Agua u otros líquidos en las partes secas del endoscopio flexible debido a agujeros, desgarros o limpieza inadecuada.", "Realiza una prueba de fugas después de cada procedimiento. Si ocurre alguna invasión de líquido, remite al técnico biomédico."),
                ]},
                {"fault": "La imagen está nublada o con puntos oscuros", "cases": [
                    ("Acumulación de materia en la lente distal.", "Limpia la lente con una toallita con alcohol."),
                    ("Fibras rotas en el cable", "Si afectan significativamente el uso, devuélvelo al fabricante."),
                ]},
                {"fault": "No se puede doblar libremente hasta el grado especificado", "cases": [
                    ("Porción del endoscopio demasiado doblada.", "No fuerces la curvatura."),
                    ("Invasión de líquido", "Remite al técnico biomédico."),
                ]},
                {"fault": "Los instrumentos no pasan fácilmente por el canal de biopsia / acceso", "cases": [
                    ("Pinzas y cepillos dañados", "Enjuaga el canal. Comprueba si hay rebabas y muescas frotando una mano enguantada sobre todas las superficies del accesorio. Remite al técnico biomédico si el problema persiste."),
                ]},
                {"fault": "La luz no funciona", "cases": [
                    ("Bombilla fundida", "Reemplaza la bombilla con el tipo correcto."),
                    ("Fusible fundido", "Reemplaza el fusible con el calibre correcto."),
                    ("Sin corriente en la toma", "Verifica que el interruptor esté encendido. Comprueba que la toma tenga corriente usando un equipo que se sepa que funciona. Contacta a un electricista para el cableado si no hay corriente."),
                ]},
                {"fault": "Descargas eléctricas", "cases": [
                    ("Fallo del cableado", "Remite al electricista."),
                ]},
            ],
            "daily": [
                "Enjuaga, lava, seca y desinfecta el endoscopio después de cada uso",
                "Retira cualquier cinta, papel o cuerpo extraño del equipo",
                "Verifica que todos los accesorios y conexiones estén correctamente conectados.",
                "Verifica que no haya signos de daño en el tubo flexible",
                "Guárdalo en el empaque correcto para su protección",
                "Verifica el funcionamiento de los controles y tubos antes del uso",
            ],
            "weekly": [
                "Enjuaga, lava, seca y desinfecta el endoscopio",
                "Realiza la prueba de fugas según las pautas del fabricante, asegurándote de que la tapa resistente al agua esté en su lugar",
                "Desenchufa la fuente de luz, límpiala con un paño húmedo y seca",
                "Inspecciona la óptica en busca de nubosidad, cuerpos extraños o puntos oscuros",
                "Verifica la solidez del carro si se usa",
                "Si algún enchufe, cable o toma está dañado, reemplázalo",
                "Verifica el funcionamiento correcto de todos los controles, indicadores y lámparas",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "infant_incubator",
        "title": "Incubators (Infant)",
        "function": (
            "An infant incubator is a closed chamber in which a controlled environment is provided "
            "to the premature or critically ill baby. The user can select the appropriate "
            "temperature, humidity and oxygen level suitable for the baby."
        ),
        "how_it_works": (
            "The general principle is that air is processed before it reaches baby. An electric "
            "fan draws room air through a bacterial filter which removes dust and bacteria. The "
            "filtered air flows over an electric heating element. The filtered and heated air then "
            "passes over a water tank where it is moistened. It then flows on to the incubator "
            "canopy. The incubator canopy is slightly pressurised. This allows expired carbon "
            "dioxide to pass back into the room via the vent holes and most of the air to be "
            "re-circulated. It also prevents unfiltered air entering the system."
        ),
        "faults": [
            {"fault": "Incubator is not running", "cases": [
                ("No power from mains socket", "Check power switch is on. Replace fuse with correct voltage and current if blown. Check mains power is present at socket using equipment known to be working. Contact electrician for rewiring if power not present."),
                ("Electrical cable fault", "Try cable on another piece of equipment. Contact electrician for repair if required."),
            ]},
            {"fault": "Fuse keeps blowing", "cases": [
                ("Power supply or cable fault", "Refer to electrician."),
            ]},
            {"fault": "Alarms not working", "cases": [
                ("Alarm battery dead", "Replace the battery and recheck. Send for repair if problem remains."),
            ]},
            {"fault": "Temperature not properly controlled", "cases": [
                ("Temperature probe and sensor not working", "Check the temperature probes and sensor connections. Replace the temperature probe and sensor and recheck."),
                ("Incubator placed in direct sunlight or near a draught / fan.", "Move incubator if placed near heat or draught."),
                ("Fan or air duct problem", "Call technician if fan not working. Unblock air duct if obstructed."),
            ]},
            {"fault": "Incubator not heating even when the heater lamp is on", "cases": [
                ("Heating element problem", "If accessible, replace heating element. Otherwise refer to technician for repair."),
            ]},
            {"fault": "Electrical shocks", "cases": [
                ("Wiring fault", "Refer to electrician immediately."),
            ]},
        ],
        "daily": [
            "Wipe dust off exterior and cover equipment after checks",
            "Remove any tape, paper or foreign body from equipment",
            "Check all fittings and accessories are mounted correctly",
            "Drain off the water tray. Run machine for 30 minutes to dry the tray. Refill tray with sterile water just before re-use.",
        ],
        "weekly": [
            "Unplug, clean outside with damp cloth and dry off",
            "Remove any dirt from wheels",
            "Wash (or replace) the air filters, dry thoroughly for reuse",
            "Check mains plug screws are tight",
            "Check mains cable has no bare wire and is not damaged",
            "Check doors, cable and tray. Repair if damaged",
            "Check all controls operate correctly",
            "Check the readings of thermometer and oxygen sensors change when breathed upon",
            "Check any batteries are working properly.",
        ],
        "fr": {
            "title": "Couveuses (incubateurs) pour nourrissons",
            "function": (
                "Une couveuse pour nourrissons est une chambre fermée dans laquelle un "
                "environnement contrôlé est fourni au bébé prématuré ou gravement malade. "
                "L'utilisateur peut choisir la température, l'humidité et le taux d'oxygène "
                "appropriés pour le bébé."
            ),
            "how_it_works": (
                "Le principe général est que l'air est traité avant d'atteindre le bébé. Un "
                "ventilateur électrique aspire l'air de la pièce à travers un filtre bactérien qui "
                "élimine la poussière et les bactéries. L'air filtré passe sur un élément "
                "chauffant électrique. L'air filtré et chauffé passe ensuite sur un réservoir "
                "d'eau où il est humidifié. Il s'écoule ensuite vers la cloche de la couveuse. La "
                "cloche de la couveuse est légèrement pressurisée. Cela permet au dioxyde de "
                "carbone expiré de retourner dans la pièce par les orifices de ventilation et à la "
                "plus grande partie de l'air d'être recirculée. Cela empêche également l'air non "
                "filtré d'entrer dans le système."
            ),
            "faults": [
                {"fault": "La couveuse ne fonctionne pas", "cases": [
                    ("Pas de courant à la prise secteur", "Vérifiez que l'interrupteur est allumé. Remplacez le fusible par un fusible de tension et de courant corrects s'il a sauté. Vérifiez que la prise est alimentée à l'aide d'un équipement connu en état de marche. Contactez un électricien pour le câblage si le courant n'est pas présent."),
                    ("Défaut de câble électrique", "Essayez le câble sur un autre équipement. Contactez un électricien pour réparation si nécessaire."),
                ]},
                {"fault": "Le fusible saute sans cesse", "cases": [
                    ("Défaut d'alimentation ou de câble", "Renvoyez à l'électricien."),
                ]},
                {"fault": "Les alarmes ne fonctionnent pas", "cases": [
                    ("Pile d'alarme déchargée", "Remplacez la pile et revérifiez. Envoyez à la réparation si le problème persiste."),
                ]},
                {"fault": "La température n'est pas correctement contrôlée", "cases": [
                    ("La sonde de température et le capteur ne fonctionnent pas", "Vérifiez les connexions des sondes de température et du capteur. Remplacez la sonde de température et le capteur puis revérifiez."),
                    ("La couveuse est placée en plein soleil ou près d'un courant d'air / ventilateur.", "Déplacez la couveuse si elle est près d'une source de chaleur ou d'un courant d'air."),
                    ("Problème de ventilateur ou de conduit d'air", "Appelez un technicien si le ventilateur ne fonctionne pas. Débouchez le conduit d'air s'il est obstrué."),
                ]},
                {"fault": "La couveuse ne chauffe pas même lorsque la lampe de chauffage est allumée", "cases": [
                    ("Problème d'élément chauffant", "S'il est accessible, remplacez l'élément chauffant. Sinon, renvoyez au technicien pour réparation."),
                ]},
                {"fault": "Chocs électriques", "cases": [
                    ("Défaut de câblage", "Renvoyez immédiatement à l'électricien."),
                ]},
            ],
            "daily": [
                "Essuyez la poussière de l'extérieur et recouvrez l'équipement après les vérifications",
                "Retirez tout ruban adhésif, papier ou corps étranger de l'équipement",
                "Vérifiez que toutes les fixations et accessoires sont correctement montés",
                "Videz le bac à eau. Faites fonctionner la machine pendant 30 minutes pour sécher le bac. Remplissez le bac d'eau stérile juste avant la réutilisation.",
            ],
            "weekly": [
                "Débranchez, nettoyez l'extérieur avec un chiffon humide et séchez",
                "Retirez toute saleté des roues",
                "Lavez (ou remplacez) les filtres à air et séchez-les soigneusement pour les réutiliser",
                "Vérifiez que les vis de la prise secteur sont bien serrées",
                "Vérifiez que le câble secteur ne présente ni fil dénudé ni dommage",
                "Vérifiez les portes, le câble et le bac. Réparez s'ils sont endommagés",
                "Vérifiez que toutes les commandes fonctionnent correctement",
                "Vérifiez que les lectures du thermomètre et des capteurs d'oxygène changent lorsqu'on souffle dessus",
                "Vérifiez que toutes les piles fonctionnent correctement.",
            ],
        },
        "es": {
            "title": "Incubadoras (neonatales)",
            "function": (
                "Una incubadora neonatal es una cámara cerrada en la que se proporciona un "
                "ambiente controlado al bebé prematuro o gravemente enfermo. El usuario puede "
                "seleccionar la temperatura, la humedad y el nivel de oxígeno adecuados para el "
                "bebé."
            ),
            "how_it_works": (
                "El principio general es que el aire se procesa antes de llegar al bebé. Un "
                "ventilador eléctrico aspira el aire de la habitación a través de un filtro "
                "bacteriano que elimina el polvo y las bacterias. El aire filtrado pasa sobre un "
                "elemento calefactor eléctrico. El aire filtrado y calentado pasa luego sobre un "
                "tanque de agua donde se humidifica. Luego fluye hacia la cúpula de la incubadora. "
                "La cúpula de la incubadora está ligeramente presurizada. Esto permite que el "
                "dióxido de carbono exhalado regrese a la habitación a través de los orificios de "
                "ventilación y que la mayor parte del aire se recircule. También evita que el aire "
                "sin filtrar entre al sistema."
            ),
            "faults": [
                {"fault": "La incubadora no funciona", "cases": [
                    ("No hay corriente en la toma de red", "Verifica que el interruptor esté encendido. Reemplaza el fusible con la tensión y corriente correctas si se ha fundido. Comprueba que la toma tenga corriente usando un equipo que se sepa que funciona. Contacta a un electricista para el cableado si no hay corriente."),
                    ("Fallo del cable eléctrico", "Prueba el cable en otro equipo. Contacta a un electricista para su reparación si es necesario."),
                ]},
                {"fault": "El fusible se funde constantemente", "cases": [
                    ("Fallo de la fuente de alimentación o del cable", "Remite al electricista."),
                ]},
                {"fault": "Las alarmas no funcionan", "cases": [
                    ("Batería de la alarma agotada", "Reemplaza la batería y vuelve a verificar. Envía a reparar si el problema persiste."),
                ]},
                {"fault": "La temperatura no se controla correctamente", "cases": [
                    ("La sonda de temperatura y el sensor no funcionan", "Verifica las conexiones de las sondas de temperatura y del sensor. Reemplaza la sonda de temperatura y el sensor y vuelve a verificar."),
                    ("La incubadora está colocada a la luz solar directa o cerca de una corriente de aire / ventilador.", "Mueve la incubadora si está cerca de calor o de una corriente de aire."),
                    ("Problema del ventilador o del conducto de aire", "Llama al técnico si el ventilador no funciona. Desbloquea el conducto de aire si está obstruido."),
                ]},
                {"fault": "La incubadora no calienta incluso cuando la lámpara de calor está encendida", "cases": [
                    ("Problema del elemento calefactor", "Si es accesible, reemplaza el elemento calefactor. De lo contrario, remite al técnico para su reparación."),
                ]},
                {"fault": "Descargas eléctricas", "cases": [
                    ("Fallo del cableado", "Remite inmediatamente al electricista."),
                ]},
            ],
            "daily": [
                "Limpia el polvo del exterior y cubre el equipo después de las verificaciones",
                "Retira cualquier cinta, papel o cuerpo extraño del equipo",
                "Verifica que todos los accesorios y conexiones estén montados correctamente",
                "Drena la bandeja de agua. Haz funcionar la máquina durante 30 minutos para secar la bandeja. Vuelve a llenar la bandeja con agua estéril justo antes de reutilizarla.",
            ],
            "weekly": [
                "Desenchufa, limpia el exterior con un paño húmedo y seca",
                "Retira cualquier suciedad de las ruedas",
                "Lava (o reemplaza) los filtros de aire y sécalos bien para reutilizarlos",
                "Verifica que los tornillos del enchufe de red estén apretados",
                "Verifica que el cable de red no tenga cables pelados ni esté dañado",
                "Revisa las puertas, el cable y la bandeja. Repara si están dañados",
                "Verifica que todos los controles funcionen correctamente",
                "Verifica que las lecturas del termómetro y de los sensores de oxígeno cambien cuando se sopla sobre ellos",
                "Verifica que todas las baterías funcionen correctamente.",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "lamp",
        "title": "Lamps",
        "function": (
            "There are many kinds of sources of light used in medicine. This chapter deals with "
            "large lights for operating theatres or delivery suites, ultraviolet or infrared "
            "phototherapy units, ophthalmic slit lamps, handheld and head worn lamps for ENT "
            "clinics and domestic torches. However, the principles here will help in the "
            "maintenance of any kind of light source."
        ),
        "how_it_works": (
            "Each type of lamp will have a power source with switch and a bulb. Some will also "
            "have controls for the brightness or focus of the light, while others will also have "
            "lenses to direct the light where required. Some lights operate off mains electricity, "
            "while others use batteries instead. Some lights have both, using the batteries for "
            "back-up power in case of mains supply failure. Electric bulbs and batteries have "
            "limited life and will need regular checking. A stock of spares should be kept of all "
            "the correct voltages and wattages (ratings) of parts."
        ),
        "faults": [
            {"fault": "No light or power on visible", "cases": [
                ("No power at mains socket", "Check power switch is on. Replace fuse with correct rating of voltage and current if blown. Check mains power is present at socket using equipment known to be working. Contact electrician for rewiring if power not present."),
                ("Dead battery", "Charge or replace batteries."),
                ("Blown bulb", "Replace bulb with correct voltage and wattage."),
                ("Battery leakage", "Remove batteries, clean battery terminals and replace with new battery."),
                ("Electrical cable fault", "Try cable on another piece of equipment. Contact electrician for repair if required."),
                ("Internal wiring fault", "Refer to electrician."),
            ]},
            {"fault": "Fuse / bulb keeps blowing", "cases": [
                ("Fuse or bulb is wrong rating", "Replace with correct rating."),
                ("Power supply or cable fault", "Refer to electrician."),
            ]},
            {"fault": "Light cannot be made bright enough", "cases": [
                ("Dirt on lens or tube", "Clean area with dry, clean cotton."),
                ("Poor power supply", "Check power line or replace batteries."),
                ("Wrong bulb rating", "Check bulb rating is correct."),
                ("Control malfunction", "Refer to electrician."),
            ]},
            {"fault": "Electrical shocks", "cases": [
                ("Wiring fault", "Refer to electrician."),
            ]},
        ],
        "daily": [
            "Wipe dust off exterior and cover equipment after checks",
            "Check all fittings and accessories are mounted correctly",
            "Check there are no cracks in glass / covers or liquid spillages",
            "If in use that day, run a brief function check before clinic",
        ],
        "weekly": [
            "Unplug, clean outside with damp cloth and dry off",
            "Clean any filters, covers and battery compartment",
            "Tighten any loose screws and check parts are fitted tightly",
            "Check mains plug screws are tight",
            "Check mains cable has no bare wire and is not damaged",
            "Check all switches operate correctly",
            "Remove or charge batteries if out of use",
        ],
        "fr": {
            "title": "Lampes",
            "function": (
                "Il existe de nombreuses sortes de sources de lumière utilisées en médecine. Ce "
                "chapitre traite des grandes lampes pour les salles d'opération ou les salles "
                "d'accouchement, des unités de photothérapie aux ultraviolets ou infrarouges, des "
                "lampes à fente ophtalmiques, des lampes portatives et frontales pour les "
                "consultations ORL et des torches domestiques. Cependant, les principes énoncés ici "
                "aideront à la maintenance de toute sorte de source lumineuse."
            ),
            "how_it_works": (
                "Chaque type de lampe possède une source d'alimentation avec un interrupteur et une "
                "ampoule. Certaines auront également des commandes pour la luminosité ou la mise au "
                "point de la lumière, tandis que d'autres auront aussi des lentilles pour diriger la "
                "lumière là où c'est nécessaire. Certaines lampes fonctionnent sur le secteur, "
                "d'autres utilisent des piles à la place. Certaines lampes ont les deux, utilisant "
                "les piles comme alimentation de secours en cas de panne du secteur. Les ampoules "
                "électriques et les piles ont une durée de vie limitée et nécessitent des "
                "vérifications régulières. Un stock de pièces de rechange doit être conservé pour "
                "toutes les tensions et puissances (calibres) correctes des pièces."
            ),
            "faults": [
                {"fault": "Pas de lumière ou de courant visible", "cases": [
                    ("Pas de courant à la prise secteur", "Vérifiez que l'interrupteur est allumé. Remplacez le fusible par un fusible de tension et de courant corrects s'il a sauté. Vérifiez que la prise est alimentée à l'aide d'un équipement connu en état de marche. Contactez un électricien pour le câblage si le courant n'est pas présent."),
                    ("Piles déchargées", "Rechargez ou remplacez les piles."),
                    ("Ampoule grillée", "Remplacez l'ampoule avec la bonne tension et puissance."),
                    ("Fuite de pile", "Retirez les piles, nettoyez les bornes et remplacez par des piles neuves."),
                    ("Défaut de câble électrique", "Essayez le câble sur un autre équipement. Contactez un électricien pour réparation si nécessaire."),
                    ("Défaut de câblage interne", "Renvoyez à l'électricien."),
                ]},
                {"fault": "Le fusible / l'ampoule saute sans cesse", "cases": [
                    ("Mauvais calibre du fusible ou de l'ampoule", "Remplacez avec le calibre correct."),
                    ("Défaut d'alimentation ou de câble", "Renvoyez à l'électricien."),
                ]},
                {"fault": "La lumière ne peut pas être rendue assez brillante", "cases": [
                    ("Saleté sur la lentille ou le tube", "Nettoyez la zone avec du coton sec et propre."),
                    ("Mauvaise alimentation électrique", "Vérifiez la ligne d'alimentation ou remplacez les piles."),
                    ("Mauvais calibre d'ampoule", "Vérifiez que le calibre de l'ampoule est correct."),
                    ("Dysfonctionnement de la commande", "Renvoyez à l'électricien."),
                ]},
                {"fault": "Chocs électriques", "cases": [
                    ("Défaut de câblage", "Renvoyez à l'électricien."),
                ]},
            ],
            "daily": [
                "Essuyez la poussière de l'extérieur et recouvrez l'équipement après les vérifications",
                "Vérifiez que toutes les fixations et accessoires sont correctement montés",
                "Vérifiez qu'il n'y a ni fissure dans le verre / les capots ni déversement de liquide",
                "S'il est utilisé ce jour-là, effectuez un bref contrôle de fonctionnement avant la consultation",
            ],
            "weekly": [
                "Débranchez, nettoyez l'extérieur avec un chiffon humide et séchez",
                "Nettoyez les filtres, capots et le compartiment des piles",
                "Resserrez les vis desserrées et vérifiez que les pièces sont bien fixées",
                "Vérifiez que les vis de la prise secteur sont bien serrées",
                "Vérifiez que le câble secteur ne présente ni fil dénudé ni dommage",
                "Vérifiez que tous les interrupteurs fonctionnent correctement",
                "Retirez ou rechargez les piles si l'appareil n'est pas utilisé",
            ],
        },
        "es": {
            "title": "Lámparas",
            "function": (
                "Hay muchos tipos de fuentes de luz utilizadas en medicina. Este capítulo trata "
                "sobre las grandes lámparas para quirófanos o salas de parto, las unidades de "
                "fototerapia ultravioleta o infrarroja, las lámparas de hendidura oftálmicas, las "
                "lámparas de mano y de cabeza para clínicas de ORL y las linternas domésticas. Sin "
                "embargo, los principios aquí descritos ayudarán en el mantenimiento de cualquier "
                "tipo de fuente de luz."
            ),
            "how_it_works": (
                "Cada tipo de lámpara tendrá una fuente de alimentación con interruptor y una "
                "bombilla. Algunas también tendrán controles para el brillo o el enfoque de la luz, "
                "mientras que otras también tendrán lentes para dirigir la luz donde se necesite. "
                "Algunas luces funcionan con electricidad de la red, mientras que otras usan baterías. "
                "Algunas luces tienen ambas, usando las baterías como energía de respaldo en caso de "
                "falla del suministro de red. Las bombillas y baterías eléctricas tienen una vida "
                "limitada y necesitarán revisiones periódicas. Se debe mantener un stock de "
                "repuestos de todos los voltajes y vatios (calibres) correctos de las piezas."
            ),
            "faults": [
                {"fault": "No se ve luz ni corriente", "cases": [
                    ("No hay corriente en la toma de red", "Verifica que el interruptor esté encendido. Reemplaza el fusible con la tensión y corriente correctas si se ha fundido. Comprueba que la toma tenga corriente usando un equipo que se sepa que funciona. Contacta a un electricista para el cableado si no hay corriente."),
                    ("Batería agotada", "Carga o reemplaza las baterías."),
                    ("Bombilla fundida", "Reemplaza la bombilla con el voltaje y vataje correctos."),
                    ("Fuga de la batería", "Retira las baterías, limpia los terminales y reemplázalas por baterías nuevas."),
                    ("Fallo del cable eléctrico", "Prueba el cable en otro equipo. Contacta a un electricista para su reparación si es necesario."),
                    ("Fallo del cableado interno", "Remite al electricista."),
                ]},
                {"fault": "El fusible / la bombilla se funde constantemente", "cases": [
                    ("El fusible o la bombilla tienen un calibre incorrecto", "Reemplaza con el calibre correcto."),
                    ("Fallo de la fuente de alimentación o del cable", "Remite al electricista."),
                ]},
                {"fault": "La luz no puede hacerse lo suficientemente brillante", "cases": [
                    ("Suciedad en la lente o el tubo", "Limpia el área con algodón seco y limpio."),
                    ("Mala fuente de alimentación", "Verifica la línea eléctrica o reemplaza las baterías."),
                    ("Calibre de bombilla incorrecto", "Verifica que el calibre de la bombilla sea correcto."),
                    ("Mal funcionamiento del control", "Remite al electricista."),
                ]},
                {"fault": "Descargas eléctricas", "cases": [
                    ("Fallo del cableado", "Remite al electricista."),
                ]},
            ],
            "daily": [
                "Limpia el polvo del exterior y cubre el equipo después de las verificaciones",
                "Verifica que todos los accesorios y conexiones estén montados correctamente",
                "Verifica que no haya grietas en el vidrio / las cubiertas ni derrames de líquidos",
                "Si se usa ese día, realiza una breve comprobación de funcionamiento antes de la consulta",
            ],
            "weekly": [
                "Desenchufa, limpia el exterior con un paño húmedo y seca",
                "Limpia los filtros, cubiertas y el compartimento de la batería",
                "Aprieta los tornillos sueltos y verifica que las piezas estén bien ajustadas",
                "Verifica que los tornillos del enchufe de red estén apretados",
                "Verifica que el cable de red no tenga cables pelados ni esté dañado",
                "Verifica que todos los interruptores funcionen correctamente",
                "Retira o carga las baterías si no se usa",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "nebulizer",
        "title": "Nebulizers",
        "function": (
            "A nebulizer is a device used to administer medication in the form of a mist inhaled "
            "into the lungs. Nebulizers are commonly used for treatment of cystic fibrosis, asthma "
            "and other respiratory diseases. The reason for using a nebulizer for medicine to be "
            "administered directly to the lungs is that small aerosol droplets can penetrate into "
            "the narrow branches of the lower airways. Large droplets would be absorbed by the "
            "mouth cavity, where the clinical effect would be low."
        ),
        "how_it_works": (
            "The common technical principle for all nebulizers is to use oxygen, compressed air or "
            "ultrasonic power as means to break up medical solutions or suspensions into small "
            "aerosol droplets. These are passed for direct inhalation either through the mouthpiece "
            "of the device or a hose set. Gas powered devices use a small pump to force the gas "
            "through the solution and will normally have a filter for the gas inlet. Ultrasonic "
            "devices use a small crystal to generate vibrations in the solution that cause "
            "droplets to break off."
        ),
        "faults": [
            {"fault": "Equipment is not working", "cases": [
                ("No power from mains socket", "Check power switch is on. Replace fuse with correct voltage and current if blown. Check mains power is present at socket using equipment known to be working. Contact electrician for rewiring if power not present."),
                ("Electrical cable fault", "Try cable on another piece of equipment. Contact electrician for repair if required."),
            ]},
            {"fault": "Machine is working but flow is absent or low", "cases": [
                ("Filter is blocked", "Clean filter."),
                ("Pipe is twisted or nebulizer chamber / mouthpiece is blocked.", "Connect pipe properly, clean chamber / mouthpiece."),
                ("Worn out pump tubing", "Replace tubing."),
                ("Compressor (or air source) is broken obstructed or leaking", "Remove any blocking material or call biomedical technician to fix the problem."),
            ]},
            {"fault": "Inadequate nebulizing amount", "cases": [
                ("Output adjustment not correctly set", "Adjust output as directed in user manual."),
                ("Mouthpiece cracked", "Replace mouthpiece."),
                ("Internal fault", "Refer to biomedical technician."),
            ]},
            {"fault": "Electrical shocks or fuse keeps blowing", "cases": [
                ("Wiring fault", "Refer to electrician."),
            ]},
        ],
        "daily": [
            "Clean and sterilize mouthpiece and medicine chamber",
            "Wipe dust from machine and replace cover after checks",
            "Check all parts are present and tightly fitted",
            "Check all moving parts move freely, all holes are unblocked",
            "Check the whole system function before use",
        ],
        "weekly": [
            "Unplug, clean outside with damp cloth and dry off",
            "Clean filter and air chamber of compressor",
            "Clean chamber and tube seals, replace if damaged",
            "If mains plug, cable or socket are damaged, replace them",
            "When next used, check for adequate nebulization.",
            "Check compressor fan is working without excessive noise.",
        ],
        "fr": {
            "title": "Nébuleurs",
            "function": (
                "Un nébuleur est un dispositif utilisé pour administrer un médicament sous forme de "
                "brume inhalée dans les poumons. Les nébuleurs sont couramment utilisés pour le "
                "traitement de la mucoviscidose, de l'asthme et d'autres maladies respiratoires. La "
                "raison d'utiliser un nébuleur pour administrer le médicament directement dans les "
                "poumons est que les petites gouttelettes d'aérosol peuvent pénétrer dans les "
                "étroites ramifications des voies aériennes inférieures. Les grosses gouttelettes "
                "seraient absorbées par la cavité buccale, où l'effet clinique serait faible."
            ),
            "how_it_works": (
                "Le principe technique commun à tous les nébuleurs est d'utiliser l'oxygène, l'air "
                "comprimé ou la puissance ultrasonique pour décomposer les solutions ou suspensions "
                "médicales en petites gouttelettes d'aérosol. Celles-ci sont administrées par "
                "inhalation directe soit à travers l'embout buccal du dispositif, soit par un "
                "ensemble de tuyaux. Les dispositifs à gaz utilisent une petite pompe pour faire "
                "passer le gaz à travers la solution et comportent normalement un filtre à l'entrée "
                "de gaz. Les dispositifs ultrasoniques utilisent un petit cristal pour générer des "
                "vibrations dans la solution qui provoquent le détachement des gouttelettes."
            ),
            "faults": [
                {"fault": "L'équipement ne fonctionne pas", "cases": [
                    ("Pas de courant à la prise secteur", "Vérifiez que l'interrupteur est allumé. Remplacez le fusible par un fusible de tension et de courant corrects s'il a sauté. Vérifiez que la prise est alimentée à l'aide d'un équipement connu en état de marche. Contactez un électricien pour le câblage si le courant n'est pas présent."),
                    ("Défaut de câble électrique", "Essayez le câble sur un autre équipement. Contactez un électricien pour réparation si nécessaire."),
                ]},
                {"fault": "La machine fonctionne mais le débit est absent ou faible", "cases": [
                    ("Filtre obstrué", "Nettoyez le filtre."),
                    ("Le tuyau est tordu ou la chambre du nébuleur / l'embout buccal est obstrué(e).", "Connectez correctement le tuyau, nettoyez la chambre / l'embout buccal."),
                    ("Tubulure de pompe usée", "Remplacez la tubulure."),
                    ("Le compresseur (ou la source d'air) est cassé, obstrué ou fuit", "Retirez tout matériau obstruant ou appelez un technicien biomédical pour résoudre le problème."),
                ]},
                {"fault": "Quantité de nébulisation inadéquate", "cases": [
                    ("Réglage de sortie incorrect", "Réglez la sortie conformément au manuel d'utilisation."),
                    ("Embout buccal fissuré", "Remplacez l'embout buccal."),
                    ("Défaut interne", "Renvoyez au technicien biomédical."),
                ]},
                {"fault": "Chocs électriques ou fusible qui saute", "cases": [
                    ("Défaut de câblage", "Renvoyez à l'électricien."),
                ]},
            ],
            "daily": [
                "Nettoyez et stérilisez l'embout buccal et la chambre à médicament",
                "Essuyez la poussière de la machine et remettez le capot après les vérifications",
                "Vérifiez que toutes les pièces sont présentes et bien fixées",
                "Vérifiez que toutes les pièces mobiles se déplacent librement et que tous les orifices sont dégagés",
                "Vérifiez le fonctionnement de tout le système avant utilisation",
            ],
            "weekly": [
                "Débranchez, nettoyez l'extérieur avec un chiffon humide et séchez",
                "Nettoyez le filtre et la chambre à air du compresseur",
                "Nettoyez la chambre et les joints des tubes, remplacez-les s'ils sont endommagés",
                "Si la fiche, le câble ou la prise secteur sont endommagés, remplacez-les",
                "À la prochaine utilisation, vérifiez une nébulisation adéquate.",
                "Vérifiez que le ventilateur du compresseur fonctionne sans bruit excessif.",
            ],
        },
        "es": {
            "title": "Nebulizadores",
            "function": (
                "Un nebulizador es un dispositivo utilizado para administrar medicamentos en forma "
                "de niebla inhalada hacia los pulmones. Los nebulizadores se usan comúnmente para el "
                "tratamiento de la fibrosis quística, el asma y otras enfermedades respiratorias. La "
                "razón para usar un nebulizador para administrar el medicamento directamente a los "
                "pulmones es que las pequeñas gotas de aerosol pueden penetrar en las ramas "
                "estrechas de las vías respiratorias inferiores. Las gotas grandes serían absorbidas "
                "por la cavidad bucal, donde el efecto clínico sería bajo."
            ),
            "how_it_works": (
                "El principio técnico común para todos los nebulizadores es usar oxígeno, aire "
                "comprimido o energía ultrasónica como medio para descomponer soluciones o "
                "suspensiones médicas en pequeñas gotas de aerosol. Estas se administran para "
                "inhalación directa a través de la boquilla del dispositivo o de un conjunto de "
                "mangueras. Los dispositivos de gas usan una pequeña bomba para forzar el gas a "
                "través de la solución y normalmente tienen un filtro en la entrada de gas. Los "
                "dispositivos ultrasónicos usan un pequeño cristal para generar vibraciones en la "
                "solución que hacen que las gotas se desprendan."
            ),
            "faults": [
                {"fault": "El equipo no funciona", "cases": [
                    ("No hay corriente en la toma de red", "Verifica que el interruptor esté encendido. Reemplaza el fusible con la tensión y corriente correctas si se ha fundido. Comprueba que la toma tenga corriente usando un equipo que se sepa que funciona. Contacta a un electricista para el cableado si no hay corriente."),
                    ("Fallo del cable eléctrico", "Prueba el cable en otro equipo. Contacta a un electricista para su reparación si es necesario."),
                ]},
                {"fault": "La máquina funciona pero el flujo está ausente o es bajo", "cases": [
                    ("El filtro está obstruido", "Limpia el filtro."),
                    ("El tubo está torcido o la cámara del nebulizador / la boquilla está obstruida.", "Conecta el tubo correctamente, limpia la cámara / la boquilla."),
                    ("Tubos de la bomba desgastados", "Reemplaza los tubos."),
                    ("El compresor (o la fuente de aire) está roto, obstruido o con fugas", "Retira cualquier material que bloquee o llama al técnico biomédico para solucionar el problema."),
                ]},
                {"fault": "Cantidad de nebulización inadecuada", "cases": [
                    ("El ajuste de salida no está configurado correctamente", "Ajusta la salida según las instrucciones del manual del usuario."),
                    ("Boquilla agrietada", "Reemplaza la boquilla."),
                    ("Fallo interno", "Remite al técnico biomédico."),
                ]},
                {"fault": "Descargas eléctricas o fusible que se funde constantemente", "cases": [
                    ("Fallo del cableado", "Remite al electricista."),
                ]},
            ],
            "daily": [
                "Limpia y esteriliza la boquilla y la cámara de medicamento",
                "Limpia el polvo de la máquina y vuelve a colocar la cubierta después de las verificaciones",
                "Verifica que todas las piezas estén presentes y bien ajustadas",
                "Verifica que todas las piezas móviles se muevan libremente y que todos los orificios estén despejados",
                "Verifica el funcionamiento de todo el sistema antes del uso",
            ],
            "weekly": [
                "Desenchufa, limpia el exterior con un paño húmedo y seca",
                "Limpia el filtro y la cámara de aire del compresor",
                "Limpia la cámara y los sellos de los tubos, reemplázalos si están dañados",
                "Si el enchufe, cable o toma de red está dañado, reemplázalos",
                "En el próximo uso, verifica una nebulización adecuada.",
                "Verifica que el ventilador del compresor funcione sin ruido excesivo.",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "oxygen_concentrator",
        "title": "Oxygen Concentrators",
        "function": (
            "An oxygen concentrator draws in room air, separates the oxygen from the other gases "
            "in the air and delivers the concentrated oxygen to the patient. When set at a rate of "
            "two litres per minute, the gas that is delivered by the concentrator is more than 90% "
            "oxygen. It is used for situations where bottled gas supply is impractical or "
            "expensive, and can be used by patients in the hospital or the home."
        ),
        "how_it_works": (
            "Atmospheric air consists of approximately 80% nitrogen and 20% oxygen. An oxygen "
            "concentrator uses air as a source of oxygen by separating these two components. It "
            "utilizes the property of zeolite granules to selectively absorb nitrogen from "
            "compressed air. Atmospheric air is gathered, filtered and raised to a pressure of 20 "
            "pounds per square inch (psi) by a compressor. The compressed air is then introduced "
            "into one of the canisters containing zeolite granules where nitrogen is selectively "
            "absorbed leaving the residual oxygen available for patient use. After about 20 "
            "seconds the supply of compressed air is automatically diverted to the second canister "
            "where the process is repeated enabling the output of oxygen to continue uninterrupted. "
            "While the pressure in the second canister is at 20 psi the pressure in the first "
            "canister is reduced to zero. This allows nitrogen to be released from the zeolite and "
            "returned into the atmosphere. The zeolite is then regenerated and ready for the next "
            "cycle. By alternating the pressure between the two canisters, a constant supply of "
            "oxygen is produced and the zeolite is continually being regenerated. Individual units "
            "have an output of up to five litres per minute with an oxygen concentration of up to 95%."
        ),
        "faults": [
            {"fault": "Unit not operating, power failure alarm sounds", "cases": [
                ("No power from mains socket", "Check mains switch is on and cable inserted. Replace fuse with correct voltage / current if blown. Check mains power is present at socket using equipment known to be working. Contact electrician for repair if required."),
                ("Concentrator circuit breaker has been set off.", "Press reset button if present."),
                ("Electrical cable fault", "Try cable on another piece of equipment. Contact electrician for repair if required."),
            ]},
            {"fault": "Unit not operating, no power failure alarm", "cases": [
                ("Alarm battery dead", "Replace battery and test as above."),
            ]},
            {"fault": "No oxygen flow", "cases": [
                ("Flow not visible", "Place tube under water and look for bubbles. If bubbles emerge steadily, gas is indeed flowing."),
                ("Tubes not connected tightly", "Check tubing and connectors are fitted tightly."),
                ("Water or matter blocking the oxygen tubing", "Remove tubing, flush through and dry out before replacing."),
                ("Blocked flow meter or humidifier bottle", "Replace meter / bottle or refer to biomedical technician."),
            ]},
            {"fault": "Temperature light or low oxygen alarm is on", "cases": [
                ("Unit overheated or obstructed", "Remove any obstruction caused by drapes, bedspread, wall, etc. Clean filters. Turn unit off, using standby oxygen system. Restart unit after 30 minutes. Call biomedical technician if problem not solved."),
            ]},
            {"fault": "Electrical shocks", "cases": [
                ("Wiring fault", "Refer to electrician."),
            ]},
        ],
        "daily": [
            "Remove any dust / dirt with damp cloth and dry off",
            "Fill humidifier bottle up to marker with clean distilled water",
            "Check all screws, connectors, tubes and parts tightly fitted",
            "Check oxygen flow before clinically required",
        ],
        "weekly": [
            "Wash filter in warm water and dry. Replace if damaged",
            "Clean humidifier bottle thoroughly and dry off",
            "Replace humidifier bottle if covered with limescale.",
            "If mains plug, cable or socket are damaged, replace",
            "Run machine for two minutes and check no alarms occur",
            "Check (see bubbles) that flow rate varies with flow control",
        ],
        "fr": {
            "title": "Concentrateurs d'oxygène",
            "function": (
                "Un concentrateur d'oxygène aspire l'air de la pièce, sépare l'oxygène des autres "
                "gaz de l'air et délivre l'oxygène concentré au patient. Lorsqu'il est réglé à un "
                "débit de deux litres par minute, le gaz délivré par le concentrateur est à plus de "
                "90 % de l'oxygène. Il est utilisé dans les situations où l'alimentation en gaz en "
                "bouteille est peu pratique ou coûteuse, et peut être utilisé par les patients à "
                "l'hôpital ou à domicile."
            ),
            "how_it_works": (
                "L'air atmosphérique est composé d'environ 80 % d'azote et 20 % d'oxygène. Un "
                "concentrateur d'oxygène utilise l'air comme source d'oxygène en séparant ces deux "
                "composants. Il exploite la propriété des granules de zéolithe à absorber "
                "sélectivement l'azote de l'air comprimé. L'air atmosphérique est collecté, filtré "
                "et porté à une pression de 20 livres par pouce carré (psi) par un compresseur. "
                "L'air comprimé est ensuite introduit dans l'un des cartouches contenant des "
                "granules de zéolithe où l'azote est sélectivement absorbé, laissant l'oxygène "
                "résiduel disponible pour le patient. Après environ 20 secondes, l'alimentation en "
                "air comprimé est automatiquement déviée vers la deuxième cartouche où le processus "
                "est répété, permettant une sortie d'oxygène ininterrompue. Pendant que la pression "
                "dans la deuxième cartouche est à 20 psi, la pression dans la première cartouche "
                "est réduite à zéro. Cela permet à l'azote d'être libéré de la zéolithe et de "
                "retourner dans l'atmosphère. La zéolithe est alors régénérée et prête pour le "
                "cycle suivant. En alternant la pression entre les deux cartouches, un apport "
                "constant d'oxygène est produit et la zéolithe est continuellement régénérée. Les "
                "unités individuelles ont une sortie allant jusqu'à cinq litres par minute avec une "
                "concentration d'oxygène allant jusqu'à 95 %."
            ),
            "faults": [
                {"fault": "L'unité ne fonctionne pas, l'alarme de coupure de courant retentit", "cases": [
                    ("Pas de courant à la prise secteur", "Vérifiez que l'interrupteur secteur est allumé et que le câble est branché. Remplacez le fusible par un fusible de tension / courant corrects s'il a sauté. Vérifiez que la prise est alimentée à l'aide d'un équipement connu en état de marche. Contactez un électricien pour réparation si nécessaire."),
                    ("Le disjoncteur du concentrateur s'est déclenché.", "Appuyez sur le bouton de réarmement s'il existe."),
                    ("Défaut de câble électrique", "Essayez le câble sur un autre équipement. Contactez un électricien pour réparation si nécessaire."),
                ]},
                {"fault": "L'unité ne fonctionne pas, pas d'alarme de coupure de courant", "cases": [
                    ("Pile d'alarme déchargée", "Remplacez la pile et testez comme ci-dessus."),
                ]},
                {"fault": "Pas de débit d'oxygène", "cases": [
                    ("Débit non visible", "Placez le tube sous l'eau et cherchez des bulles. Si des bulles émergent régulièrement, le gaz circule bien."),
                    ("Tubes mal raccordés", "Vérifiez que les tubulures et connecteurs sont bien fixés."),
                    ("Eau ou matière obstruant la tubulure d'oxygène", "Retirez la tubulure, rincez-la et séchez-la avant de la remettre."),
                    ("Débitmètre ou flacon humidificateur obstrué", "Remplacez le débitmètre / flacon ou renvoyez au technicien biomédical."),
                ]},
                {"fault": "Le voyant de température ou l'alarme de faible oxygène est allumé", "cases": [
                    ("L'unité a surchauffé ou est obstruée", "Retirez toute obstruction causée par les rideaux, la couverture, le mur, etc. Nettoyez les filtres. Éteignez l'unité en utilisant le système d'oxygène de secours. Redémarrez l'unité après 30 minutes. Appelez un technicien biomédical si le problème n'est pas résolu."),
                ]},
                {"fault": "Chocs électriques", "cases": [
                    ("Défaut de câblage", "Renvoyez à l'électricien."),
                ]},
            ],
            "daily": [
                "Enlevez toute poussière / saleté avec un chiffon humide et séchez",
                "Remplissez le flacon humidificateur jusqu'au repère avec de l'eau distillée propre",
                "Vérifiez que toutes les vis, connecteurs, tubes et pièces sont bien serrés",
                "Vérifiez le débit d'oxygène avant le besoin clinique",
            ],
            "weekly": [
                "Lavez le filtre à l'eau tiède et séchez-le. Remplacez-le s'il est endommagé",
                "Nettoyez soigneusement le flacon humidificateur et séchez-le",
                "Remplacez le flacon humidificateur s'il est recouvert de tartre.",
                "Si la fiche, le câble ou la prise secteur sont endommagés, remplacez-les",
                "Faites fonctionner la machine pendant deux minutes et vérifiez qu'aucune alarme ne se déclenche",
                "Vérifiez (voir les bulles) que le débit varie avec la commande de débit",
            ],
        },
        "es": {
            "title": "Concentradores de oxígeno",
            "function": (
                "Un concentrador de oxígeno aspira el aire de la habitación, separa el oxígeno de "
                "los otros gases del aire y administra el oxígeno concentrado al paciente. Cuando se "
                "configura a un ritmo de dos litros por minuto, el gas administrado por el "
                "concentrador es más de un 90 % de oxígeno. Se utiliza en situaciones donde el "
                "suministro de gas en botellas es poco práctico o costoso, y puede ser usado por "
                "pacientes en el hospital o en el hogar."
            ),
            "how_it_works": (
                "El aire atmosférico se compone de aproximadamente un 80 % de nitrógeno y un 20 % de "
                "oxígeno. Un concentrador de oxígeno utiliza el aire como fuente de oxígeno "
                "separando estos dos componentes. Aprovecha la propiedad de los gránulos de zeolita "
                "de absorber selectivamente el nitrógeno del aire comprimido. El aire atmosférico se "
                "recoge, se filtra y se eleva a una presión de 20 libras por pulgada cuadrada (psi) "
                "mediante un compresor. El aire comprimido se introduce luego en uno de los "
                "cánisters que contienen gránulos de zeolita, donde el nitrógeno se absorbe "
                "selectivamente, dejando el oxígeno residual disponible para el paciente. Después de "
                "unos 20 segundos, el suministro de aire comprimido se desvía automáticamente al "
                "segundo cánister, donde se repite el proceso, permitiendo que la salida de oxígeno "
                "continúe sin interrupciones. Mientras la presión en el segundo cánister está a 20 "
                "psi, la presión en el primer cánister se reduce a cero. Esto permite que el "
                "nitrógeno se libere de la zeolita y regrese a la atmósfera. La zeolita se "
                "regenera y queda lista para el siguiente ciclo. Al alternar la presión entre los "
                "dos cánisters, se produce un suministro constante de oxígeno y la zeolita se "
                "regenera continuamente. Las unidades individuales tienen una salida de hasta cinco "
                "litros por minuto con una concentración de oxígeno de hasta el 95 %."
            ),
            "faults": [
                {"fault": "La unidad no funciona, suena la alarma de falla de energía", "cases": [
                    ("No hay corriente en la toma de red", "Verifica que el interruptor de red esté encendido y el cable insertado. Reemplaza el fusible con la tensión / corriente correctas si se ha fundido. Comprueba que la toma tenga corriente usando un equipo que se sepa que funciona. Contacta a un electricista para su reparación si es necesario."),
                    ("El disyuntor del concentrador se ha disparado.", "Presiona el botón de reinicio si existe."),
                    ("Fallo del cable eléctrico", "Prueba el cable en otro equipo. Contacta a un electricista para su reparación si es necesario."),
                ]},
                {"fault": "La unidad no funciona, sin alarma de falla de energía", "cases": [
                    ("Batería de la alarma agotada", "Reemplaza la batería y prueba como arriba."),
                ]},
                {"fault": "Sin flujo de oxígeno", "cases": [
                    ("Flujo no visible", "Coloca el tubo bajo el agua y busca burbujas. Si las burbujas emergen de manera constante, el gas sí está fluyendo."),
                    ("Tubos no conectados firmemente", "Verifica que los tubos y conectores estén bien ajustados."),
                    ("Agua o materia bloqueando el tubo de oxígeno", "Retira el tubo, enjuágalo y sécalo antes de reemplazarlo."),
                    ("Medidor de flujo o botella humidificadora obstruidos", "Reemplaza el medidor / la botella o remite al técnico biomédico."),
                ]},
                {"fault": "La luz de temperatura o la alarma de bajo oxígeno está encendida", "cases": [
                    ("La unidad se sobrecalentó o está obstruida", "Retira cualquier obstrucción causada por cortinas, colchas, paredes, etc. Limpia los filtros. Apaga la unidad usando el sistema de oxígeno de respaldo. Reinicia la unidad después de 30 minutos. Llama al técnico biomédico si el problema no se resuelve."),
                ]},
                {"fault": "Descargas eléctricas", "cases": [
                    ("Fallo del cableado", "Remite al electricista."),
                ]},
            ],
            "daily": [
                "Elimina cualquier polvo / suciedad con un paño húmedo y seca",
                "Llena la botella humidificadora hasta la marca con agua destilada limpia",
                "Verifica que todos los tornillos, conectores, tubos y piezas estén bien apretados",
                "Verifica el flujo de oxígeno antes de la necesidad clínica",
            ],
            "weekly": [
                "Lava el filtro en agua tibia y seca. Reemplázalo si está dañado",
                "Limpia a fondo la botella humidificadora y seca",
                "Reemplaza la botella humidificadora si está cubierta de sarro.",
                "Si el enchufe, cable o toma de red está dañado, reemplázalo",
                "Haz funcionar la máquina durante dos minutos y verifica que no ocurran alarmas",
                "Verifica (viendo las burbujas) que el flujo varíe con el control de flujo",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "oxygen_cylinder_flowmeter",
        "title": "Oxygen Cylinders and Flowmeters",
        "function": (
            "Oxygen cylinders and flowmeters supply oxygen to the patient from pressurised gas "
            "bottles. The flowmeter controls the flow of oxygen delivered to the patient, "
            "typically 0 to 15 litres per minute. This setup is used when an oxygen concentrator "
            "is not available or as a standby supply system."
        ),
        "how_it_works": (
            "An oxygen cylinder stores oxygen at high pressure (around 2,000 pounds per square "
            "inch). A pressure regulator reduces this high pressure to a safe working pressure. "
            "The flowmeter, located downstream of the regulator, allows the user to adjust the "
            "flow of oxygen. The cylinder is fitted with a valve that must be opened to allow "
            "flow. Readings on the regulator pressure gauge indicate the remaining pressure in "
            "the cylinder."
        ),
        "faults": [
            {"fault": "No oxygen is flowing", "cases": [
                ("Empty cylinder. Flow meter knob or cylinder valve is closed. Faulty regulator", "Replace cylinder. Open valves, then check flow meter registers flow. Close all valves and replace regulator."),
            ]},
            {"fault": "Leakage from cylinder or flowmeter", "cases": [
                ("Cylinder is not connected to pressure regulator properly. Faulty or missing washer between regulator and cylinder. Flowmeter seal damaged or loose. Cylinder faulty", "Tighten all fittings. Replace washer. Tighten flowmeter. Label faulty and return to manufacturer."),
            ]},
            {"fault": "Leakage cannot be located", "cases": [
                ("Leakage too small to be heard", "Apply detergent solution (NOT oily soap) to joints. Bubbles will show at leak point. Clean/replace washer and tighten at that joint."),
            ]},
            {"fault": "Flowmeter ball not moving, yet oxygen is flowing", "cases": [
                ("Faulty flow meter", "Close all valves, disconnect flowmeter and clean inside. Reconnect and test. If problem persists, replace flowmeter."),
            ]},
            {"fault": "Pressure gauge does not show pressure, yet oxygen is flowing", "cases": [
                ("Faulty pressure gauge", "Refer to biomedical technician for replacement."),
            ]},
        ],
        "daily": [
            "Ensure delivery tubes and masks are sterile",
            "If humidifier bottle is used, refill with clean water",
            "Check cylinder is correct type and marked oxygen",
            "Check all parts are fitted tightly and correctly",
            "Before use, ensure cylinder is filled and flow is present",
            "Close cylinder valve after each use.",
        ],
        "weekly": [
            "Clean cylinder, valve and flowmeter with damp cloth",
            "Check for leakage: hissing sound or reduction in pressure",
            "Remove valve dust with brief, fast oxygen flow",
            "Check flow can be varied using flow control",
        ],
        "fr": {
            "title": "Bouteilles d'oxygène et débitmètres",
            "function": (
                "Les bouteilles d'oxygène et les débitmètres fournissent de l'oxygène au patient à "
                "partir de bouteilles de gaz sous pression. Le débitmètre contrôle le débit "
                "d'oxygène délivré au patient, généralement de 0 à 15 litres par minute. Cette "
                "configuration est utilisée lorsqu'un concentrateur d'oxygène n'est pas disponible "
                "ou comme système d'alimentation de secours."
            ),
            "how_it_works": (
                "Une bouteille d'oxygène stocke l'oxygène à haute pression (environ 2 000 livres par "
                "pouce carré). Un détendeur (régulateur) réduit cette pression élevée à une "
                "pression d'utilisation sûre. Le débitmètre, situé en aval du détendeur, permet à "
                "l'utilisateur de régler le débit d'oxygène. La bouteille est équipée d'une vanne "
                "qui doit être ouverte pour permettre l'écoulement. Les lectures du manomètre du "
                "détendeur indiquent la pression restante dans la bouteille."
            ),
            "faults": [
                {"fault": "Aucun écoulement d'oxygène", "cases": [
                    ("Bouteille vide. Bouton du débitmètre ou vanne de la bouteille fermé(e). Détendeur défectueux", "Remplacez la bouteille. Ouvrez les vannes, puis vérifiez que le débitmètre enregistre un débit. Fermez toutes les vannes et remplacez le détendeur."),
                ]},
                {"fault": "Fuite de la bouteille ou du débitmètre", "cases": [
                    ("La bouteille n'est pas correctement raccordée au détendeur. Rondelle défectueuse ou manquante entre le détendeur et la bouteille. Joint du débitmètre endommagé ou desserré. Bouteille défectueuse", "Serrez tous les raccords. Remplacez la rondelle. Serrez le débitmètre. Étiquetez comme défectueux et retournez au fabricant."),
                ]},
                {"fault": "La fuite ne peut pas être localisée", "cases": [
                    ("Fuite trop petite pour être entendue", "Appliquez une solution détergente (PAS de savon gras) sur les joints. Des bulles apparaîtront au point de fuite. Nettoyez / remplacez la rondelle et serrez à ce joint."),
                ]},
                {"fault": "La bille du débitmètre ne bouge pas, pourtant l'oxygène s'écoule", "cases": [
                    ("Débitmètre défectueux", "Fermez toutes les vannes, débranchez le débitmètre et nettoyez l'intérieur. Rebranchez et testez. Si le problème persiste, remplacez le débitmètre."),
                ]},
                {"fault": "Le manomètre n'indique pas la pression, pourtant l'oxygène s'écoule", "cases": [
                    ("Manomètre défectueux", "Adressez-vous au technicien biomédical pour le remplacement."),
                ]},
            ],
            "daily": [
                "Assurez-vous que les tubulures et masques de distribution sont stériles",
                "Si un flacon humidificateur est utilisé, remplissez-le d'eau propre",
                "Vérifiez que la bouteille est du bon type et marquée oxygène",
                "Vérifiez que toutes les pièces sont bien fixées et correctes",
                "Avant utilisation, assurez-vous que la bouteille est remplie et que le débit est présent",
                "Fermez la vanne de la bouteille après chaque utilisation.",
            ],
            "weekly": [
                "Nettoyez la bouteille, la vanne et le débitmètre avec un chiffon humide",
                "Vérifiez les fuites : sifflement ou baisse de pression",
                "Éliminez la poussière de la vanne par un bref débit d'oxygène rapide",
                "Vérifiez que le débit peut être modifié à l'aide de la commande de débit",
            ],
        },
        "es": {
            "title": "Cilindros de oxígeno y caudalímetros",
            "function": (
                "Los cilindros de oxígeno y los caudalímetros suministran oxígeno al paciente desde "
                "botellas de gas a presión. El caudalímetro controla el flujo de oxígeno entregado "
                "al paciente, normalmente de 0 a 15 litros por minuto. Esta configuración se usa "
                "cuando un concentrador de oxígeno no está disponible o como sistema de suministro "
                "de respaldo."
            ),
            "how_it_works": (
                "Un cilindro de oxígeno almacena oxígeno a alta presión (alrededor de 2000 libras "
                "por pulgada cuadrada). Un regulador reduce esta alta presión a una presión de "
                "servicio segura. El caudalímetro, ubicado aguas abajo del regulador, permite al "
                "usuario ajustar el flujo de oxígeno. El cilindro está equipado con una válvula que "
                "debe abrirse para permitir el flujo. Las lecturas del manómetro del regulador "
                "indican la presión restante en el cilindro."
            ),
            "faults": [
                {"fault": "No fluye oxígeno", "cases": [
                    ("Cilindro vacío. La perilla del caudalímetro o la válvula del cilindro está cerrada. Regulador defectuoso", "Reemplaza el cilindro. Abre las válvulas y luego verifica que el caudalímetro registre flujo. Cierra todas las válvulas y reemplaza el regulador."),
                ]},
                {"fault": "Fuga del cilindro o del caudalímetro", "cases": [
                    ("El cilindro no está conectado correctamente al regulador de presión. Arandela defectuosa o faltante entre el regulador y el cilindro. Sello del caudalímetro dañado o flojo. Cilindro defectuoso", "Aprieta todas las conexiones. Reemplaza la arandela. Aprieta el caudalímetro. Etiqueta como defectuoso y devuélvelo al fabricante."),
                ]},
                {"fault": "La fuga no se puede localizar", "cases": [
                    ("La fuga es demasiado pequeña para oírse", "Aplica solución detergente (NO jabón graso) en las juntas. Las burbujas aparecerán en el punto de fuga. Limpia / reemplaza la arandela y aprieta en esa junta."),
                ]},
                {"fault": "La bola del caudalímetro no se mueve, aunque el oxígeno fluye", "cases": [
                    ("Caudalímetro defectuoso", "Cierra todas las válvulas, desconecta el caudalímetro y limpia el interior. Reconecta y prueba. Si el problema persiste, reemplaza el caudalímetro."),
                ]},
                {"fault": "El manómetro no muestra presión, aunque el oxígeno fluye", "cases": [
                    ("Manómetro defectuoso", "Consulta al técnico biomédico para su reemplazo."),
                ]},
            ],
            "daily": [
                "Asegúrate de que los tubos y mascarillas de entrega estén estériles",
                "Si se usa la botella humidificadora, rellénala con agua limpia",
                "Verifica que el cilindro sea del tipo correcto y esté marcado como oxígeno",
                "Verifica que todas las piezas estén bien ajustadas y correctas",
                "Antes de usar, asegúrate de que el cilindro esté lleno y haya flujo",
                "Cierra la válvula del cilindro después de cada uso.",
            ],
            "weekly": [
                "Limpia el cilindro, la válvula y el caudalímetro con un paño húmedo",
                "Verifica si hay fugas: sonido sibilante o reducción de presión",
                "Elimina el polvo de la válvula con un flujo de oxígeno breve y rápido",
                "Verifica que el flujo pueda variarse usando el control de flujo",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "pulse_oximeter",
        "title": "Pulse Oximeters",
        "function": (
            "A pulse oximeter is used to continuously measure a patient's oxygen saturation "
            "(SpO2) and pulse. The monitor displays both the SpO2 value and the pulse rate. "
            "Oxygen saturation is a measure of how much oxygen the blood is carrying; normal "
            "values are between 95% and 100%. The device is also used to sound alarms when the "
            "oxygen saturation falls below a preset value or when the probe is disconnected."
        ),
        "how_it_works": (
            "The pulse oximeter works on the principle that oxygenated and deoxygenated blood "
            "absorb light of different wavelengths to different degrees. The probe contains a "
            "light source of two different wavelengths (red and infrared) and a light detector. "
            "The probe is placed on the patient's finger or ear. Light passes through the tissue "
            "and is detected on the other side. The difference in absorption during the pulse and "
            "between pulses allows the oxygen saturation and pulse rate to be calculated. An "
            "audible and visual alarm sounds if the measured value is outside the set limits or "
            "if the probe is disconnected."
        ),
        "faults": [
            {"fault": "Equipment is not running", "cases": [
                ("No power from mains socket. Battery (if present) is discharged. Electrical cable fault", "Check power switch is on. Replace fuse with correct voltage and current if blown. Check mains power is present at socket using equipment known to be working. Contact electrician for rewiring if power not present. Recharge or replace battery. Try cable on another piece of equipment. Contact electrician for repair if required."),
            ]},
            {"fault": "SpO2 or pulse rate not displayed or unstable", "cases": [
                ("Probe is not mounted correctly. Probe not able to read through dirt, nail polish, etc.", "Connect probe and cable properly. Remove grease, dirt, nail polish and clean probe."),
                ("Patient movement", "Request patient to remain still."),
                ("Patient's SpO2 value is too low to be measured", "Further clinical examination of patient. Resite probe if necessary."),
                ("Internal malfunction", "Call biomedical technician."),
            ]},
            {"fault": "Probe off displayed on screen", "cases": [
                ("Probe is not connected properly. The connection between the probe and oximeter is loose", "Connect the sensor. Refer to biomedical technician for repair."),
            ]},
            {"fault": "Error displayed on screen", "cases": [
                ("Faulty probe or control circuit", "Refer to biomedical technician."),
            ]},
            {"fault": "Continuous alarm sounds", "cases": [
                ("Alarm limits set too low or high. Power disconnected. Internal malfunction", "Set appropriate alarm limits. Connect power cable. Refer to biomedical technician."),
            ]},
            {"fault": "Electrical shocks", "cases": [
                ("Wiring fault", "Refer to biomedical technician immediately."),
            ]},
        ],
        "daily": [
            "Remove any dust / dirt and replace equipment cover",
            "Remove any tape, paper or foreign body from equipment",
            "Clean probe with alcohol wipe after each use",
            "Check all parts are present and connected",
            "Check cables are not twisted and remove from service if any damage is visible",
            "Check operation on healthy subject before use",
        ],
        "weekly": [
            "Unplug, clean outside with damp cloth and dry off",
            "Tighten any loose screws and check parts are fitted tightly",
            "If plug, cable or socket are damaged, replace",
            "Check operation of all lights, indicators and visual displays",
            "Check probe disconnection alarm.",
        ],
        "fr": {
            "title": "Oxymètres de pouls",
            "function": (
                "Un oxymètre de pouls est utilisé pour mesurer en continu la saturation en oxygène "
                "(SpO2) et le pouls d'un patient. Le moniteur affiche à la fois la valeur de SpO2 "
                "et la fréquence du pouls. La saturation en oxygène est une mesure de la quantité "
                "d'oxygène transportée par le sang ; des valeurs normales se situent entre 95 % et "
                "100 %. Le dispositif est également utilisé pour déclencher des alarmes lorsque la "
                "saturation en oxygène tombe sous une valeur prédéfinie ou en cas de déconnexion de "
                "la sonde."
            ),
            "how_it_works": (
                "L'oxymètre de pouls fonctionne selon le principe que le sang oxygéné et le sang "
                "désoxygéné absorbent la lumière de différentes longueurs d'onde à des degrés "
                "différents. La sonde contient une source de lumière à deux longueurs d'onde "
                "différentes (rouge et infrarouge) et un détecteur de lumière. La sonde est placée "
                "sur le doigt ou l'oreille du patient. La lumière traverse le tissu et est détectée "
                "de l'autre côté. La différence d'absorption pendant le pouls et entre les pulsations "
                "permet de calculer la saturation en oxygène et la fréquence du pouls. Une alarme "
                "sonore et visuelle est déclenchée si la valeur mesurée se situe en dehors des "
                "limites définies ou si la sonde est déconnectée."
            ),
            "faults": [
                {"fault": "L'équipement ne fonctionne pas", "cases": [
                    ("Pas de courant à la prise secteur. Pile (si présente) déchargée. Défaut de câble électrique", "Vérifiez que l'interrupteur est allumé. Remplacez le fusible par un fusible de tension et de courant corrects s'il a sauté. Vérifiez que le courant est présent à la prise à l'aide d'un équipement connu en état de marche. Contactez un électricien pour le câblage si le courant n'est pas présent. Rechargez ou remplacez la pile. Essayez le câble sur un autre équipement. Contactez un électricien pour réparation si nécessaire."),
                ]},
                {"fault": "La SpO2 ou la fréquence du pouls n'est pas affichée ou est instable", "cases": [
                    ("La sonde n'est pas montée correctement. La sonde ne peut pas lire à travers la saleté, le vernis à ongles, etc.", "Connectez correctement la sonde et le câble. Retirez la graisse, la saleté, le vernis à ongles et nettoyez la sonde."),
                    ("Mouvement du patient", "Demandez au patient de rester immobile."),
                    ("La valeur de SpO2 du patient est trop basse pour être mesurée", "Examen clinique complémentaire du patient. Replacez la sonde si nécessaire."),
                    ("Dysfonctionnement interne", "Appelez le technicien biomédical."),
                ]},
                {"fault": "« Sonde débranchée » affiché à l'écran", "cases": [
                    ("La sonde n'est pas connectée correctement. La connexion entre la sonde et l'oxymètre est desserrée", "Connectez le capteur. Adressez-vous au technicien biomédical pour réparation."),
                ]},
                {"fault": "Erreur affichée à l'écran", "cases": [
                    ("Sonde ou circuit de commande défectueux", "Adressez-vous au technicien biomédical."),
                ]},
                {"fault": "Alarme continue", "cases": [
                    ("Limites d'alarme réglées trop basses ou trop hautes. Alimentation coupée. Dysfonctionnement interne", "Réglez des limites d'alarme appropriées. Branchez le câble d'alimentation. Adressez-vous au technicien biomédical."),
                ]},
                {"fault": "Chocs électriques", "cases": [
                    ("Défaut de câblage", "Adressez-vous immédiatement au technicien biomédical."),
                ]},
            ],
            "daily": [
                "Retirez toute poussière / saleté et replacez le capot de l'équipement",
                "Retirez tout ruban adhésif, papier ou corps étranger de l'équipement",
                "Nettoyez la sonde avec une lingette alcoolisée après chaque utilisation",
                "Vérifiez que toutes les pièces sont présentes et connectées",
                "Vérifiez que les câbles ne sont pas entortillés et retirez du service tout câble présentant des dommages visibles",
                "Vérifiez le fonctionnement sur un sujet sain avant utilisation",
            ],
            "weekly": [
                "Débranchez, nettoyez l'extérieur avec un chiffon humide et séchez",
                "Serrez les vis desserrées et vérifiez que les pièces sont bien fixées",
                "Si la fiche, le câble ou la prise sont endommagés, remplacez-les",
                "Vérifiez le fonctionnement de tous les voyants, indicateurs et affichages",
                "Vérifiez l'alarme de déconnexion de la sonde.",
            ],
        },
        "es": {
            "title": "Oximetros de pulso",
            "function": (
                "Un oximetro de pulso se utiliza para medir continuamente la saturación de oxígeno "
                "(SpO2) y el pulso de un paciente. El monitor muestra tanto el valor de SpO2 como la "
                "frecuencia del pulso. La saturación de oxígeno es una medida de cuánto oxígeno "
                "transporta la sangre; los valores normales están entre 95 % y 100 %. El dispositivo "
                "también se usa para hacer sonar alarmas cuando la saturación de oxígeno cae por "
                "debajo de un valor preestablecido o cuando la sonda se desconecta."
            ),
            "how_it_works": (
                "El oximetro de pulso funciona según el principio de que la sangre oxigenada y la "
                "sangre desoxigenada absorben luz de diferentes longitudes de onda en distinto "
                "grado. La sonda contiene una fuente de luz de dos longitudes de onda diferentes "
                "(rojo e infrarrojo) y un detector de luz. La sonda se coloca en el dedo o en la "
                "oreja del paciente. La luz atraviesa el tejido y se detecta al otro lado. La "
                "diferencia en la absorción durante el pulso y entre los pulsos permite calcular la "
                "saturación de oxígeno y la frecuencia del pulso. Una alarma sonora y visual se "
                "activa si el valor medido está fuera de los límites configurados o si la sonda se "
                "desconecta."
            ),
            "faults": [
                {"fault": "El equipo no funciona", "cases": [
                    ("No hay corriente en la toma de red. Batería (si existe) agotada. Fallo del cable eléctrico", "Verifica que el interruptor esté encendido. Reemplaza el fusible con la tensión y corriente correctas si se ha fundido. Verifica que haya corriente en la toma usando un equipo que se sepa que funciona. Contacta a un electricista para el cableado si no hay corriente. Recarga o reemplaza la batería. Prueba el cable en otro equipo. Contacta a un electricista para su reparación si es necesario."),
                ]},
                {"fault": "SpO2 o frecuencia del pulso no mostradas o inestables", "cases": [
                    ("La sonda no está montada correctamente. La sonda no puede leer a través de suciedad, esmalte de uñas, etc.", "Conecta la sonda y el cable correctamente. Retira grasa, suciedad, esmalte de uñas y limpia la sonda."),
                    ("Movimiento del paciente", "Solicita al paciente que permanezca quieto."),
                    ("El valor de SpO2 del paciente es demasiado bajo para medirse", "Examen clínico adicional del paciente. Reubica la sonda si es necesario."),
                    ("Mal funcionamiento interno", "Llama al técnico biomédico."),
                ]},
                {"fault": "Sonda desconectada mostrada en la pantalla", "cases": [
                    ("La sonda no está conectada correctamente. La conexión entre la sonda y el oximetro está floja", "Conecta el sensor. Consulta al técnico biomédico para la reparación."),
                ]},
                {"fault": "Error mostrado en la pantalla", "cases": [
                    ("Sonda o circuito de control defectuosos", "Consulta al técnico biomédico."),
                ]},
                {"fault": "Suena una alarma continua", "cases": [
                    ("Los límites de la alarma están configurados demasiado bajos o altos. Corriente desconectada. Mal funcionamiento interno", "Configura los límites de alarma apropiados. Conecta el cable de corriente. Consulta al técnico biomédico."),
                ]},
                {"fault": "Descargas eléctricas", "cases": [
                    ("Fallo del cableado", "Consulta inmediatamente al técnico biomédico."),
                ]},
            ],
            "daily": [
                "Elimina cualquier polvo / suciedad y vuelve a colocar la cubierta del equipo",
                "Retira cualquier cinta, papel o cuerpo extraño del equipo",
                "Limpia la sonda con una toallita de alcohol después de cada uso",
                "Verifica que todas las piezas estén presentes y conectadas",
                "Verifica que los cables no estén retorcidos y retira del servicio si se ve cualquier daño",
                "Verifica el funcionamiento en un sujeto sano antes del uso",
            ],
            "weekly": [
                "Desenchufa, limpia el exterior con un paño húmedo y seca",
                "Aprieta cualquier tornillo flojo y verifica que las piezas estén bien ajustadas",
                "Si el enchufe, cable o toma están dañados, reemplázalos",
                "Verifica el funcionamiento de todas las luces, indicadores y pantallas",
                "Verifica la alarma de desconexión de la sonda.",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "scale",
        "title": "Scales",
        "function": (
            "A scale is used to measure the weight of a patient. Accurate weight monitoring is "
            "important for assessing the patient's general condition and the effectiveness of "
            "treatment, and for calculating drug dosages."
        ),
        "how_it_works": (
            "Mechanical scales use a system of springs or counterweights to determine the weight, "
            "which is displayed on a dial. Electronic scales use load cells that convert the "
            "applied force into an electrical signal, displayed digitally. Both types must be "
            "level to give accurate readings and must be set to zero before use."
        ),
        "faults": [
            {"fault": "Zero point cannot be set", "cases": [
                ("Scales are not level", "Set scales on level ground and retest."),
                ("Zero control broken or internal part jammed", "Send for repair."),
            ]},
            {"fault": "Movement is stiff or jerky", "cases": [
                ("Dirt lodged inside", "Remove any visible dirt or foreign body and retest."),
                ("Internal blockage", "Send for repair."),
            ]},
            {"fault": "Reading is inaccurate", "cases": [
                ("Zero not properly set", "Reset zero and retest."),
                ("Calibration error", "Recalibrate or send for repair."),
            ]},
            {"fault": "Electronic display is blank", "cases": [
                ("Battery / power failed", "Replace battery or power supply and retest."),
                ("Internal error", "Send for repair."),
            ]},
        ],
        "daily": [
            "Wipe off dust and replace dust cover after checks",
            "Clear away any dirt or hair on controls and feet",
            "If bent, cracked or damaged, send for repair",
            "Check zero at start of day and before each patient",
        ],
        "weekly": [
            "Clean exterior with damp cloth and dry off",
            "Clean off then repaint any exposed or rusted metal",
            "Tighten any loose screws and check parts are fitted tightly",
            "Check reading is accurate using a known weight",
            "Send for repair if inaccurate or sticking",
            "Replace battery if display shows low battery",
        ],
        "fr": {
            "title": "Pèse-personnes",
            "function": (
                "Un pèse-personne est utilisé pour mesurer le poids d'un patient. Un suivi précis du "
                "poids est important pour l'évaluation de l'état général du patient et l'efficacité "
                "du traitement, et pour calculer les posologies."
            ),
            "how_it_works": (
                "Les pèse-personnes mécaniques utilisent un système de ressorts ou de contrepoids "
                "pour déterminer le poids, affiché sur un cadran. Les pèse-personnes électroniques "
                "utilisent des capteurs de charge qui convertissent la force appliquée en un signal "
                "électrique, affiché numériquement. Les deux types doivent être de niveau pour "
                "donner des lectures précises et doivent être mis à zéro avant utilisation."
            ),
            "faults": [
                {"fault": "Le point zéro ne peut pas être réglé", "cases": [
                    ("Le pèse-personne n'est pas de niveau", "Posez le pèse-personne sur un sol de niveau et retestez."),
                    ("Commande de zéro cassée ou pièce interne bloquée", "Envoyez pour réparation."),
                ]},
                {"fault": "Le mouvement est raide ou saccadé", "cases": [
                    ("Saleté logée à l'intérieur", "Retirez toute saleté ou corps étranger visible et retestez."),
                    ("Blocage interne", "Envoyez pour réparation."),
                ]},
                {"fault": "La lecture est inexacte", "cases": [
                    ("Zéro mal réglé", "Remettez à zéro et retestez."),
                    ("Erreur d'étalonnage", "Réétalonnez ou envoyez pour réparation."),
                ]},
                {"fault": "L'affichage électronique est vide", "cases": [
                    ("Pile / alimentation défaillante", "Remplacez la pile ou l'alimentation et retestez."),
                    ("Erreur interne", "Envoyez pour réparation."),
                ]},
            ],
            "daily": [
                "Essuyez la poussière et replacez le cache anti-poussière après les vérifications",
                "Dégagez toute saleté ou cheveu sur les commandes et les pieds",
                "S'il est plié, fissuré ou endommagé, envoyez-le pour réparation",
                "Vérifiez le zéro au début de la journée et avant chaque patient",
            ],
            "weekly": [
                "Nettoyez l'extérieur avec un chiffon humide et séchez",
                "Nettoyez puis repeignez tout métal exposé ou rouillé",
                "Serrez les vis desserrées et vérifiez que les pièces sont bien fixées",
                "Vérifiez que la lecture est précise à l'aide d'un poids connu",
                "Envoyez pour réparation si la lecture est inexacte ou si la balance accroche",
                "Remplacez la pile si l'affichage indique une pile faible",
            ],
        },
        "es": {
            "title": "Básculas",
            "function": (
                "Una báscula se utiliza para medir el peso de un paciente. El seguimiento preciso "
                "del peso es importante para evaluar la condición general del paciente y la "
                "efectividad del tratamiento, y para calcular las dosis de medicamentos."
            ),
            "how_it_works": (
                "Las básculas mecánicas usan un sistema de resortes o contrapesos para determinar el "
                "peso, que se muestra en una esfera. Las básculas electrónicas usan celdas de carga "
                "que convierten la fuerza aplicada en una señal eléctrica, mostrada digitalmente. "
                "Ambos tipos deben estar nivelados para dar lecturas precisas y deben ponerse a "
                "cero antes de su uso."
            ),
            "faults": [
                {"fault": "El punto cero no puede ajustarse", "cases": [
                    ("La báscula no está nivelada", "Coloca la báscula en un terreno nivelado y vuelve a probar."),
                    ("Control de cero roto o pieza interna atascada", "Enviar a reparar."),
                ]},
                {"fault": "El movimiento es rígido o entrecortado", "cases": [
                    ("Suciedad atrapada en el interior", "Retira cualquier suciedad o cuerpo extraño visible y vuelve a probar."),
                    ("Bloqueo interno", "Enviar a reparar."),
                ]},
                {"fault": "La lectura es inexacta", "cases": [
                    ("El cero no está ajustado correctamente", "Reajusta el cero y vuelve a probar."),
                    ("Error de calibración", "Recalibra o envía a reparar."),
                ]},
                {"fault": "La pantalla electrónica está en blanco", "cases": [
                    ("Batería / alimentación falló", "Reemplaza la batería o la fuente de alimentación y vuelve a probar."),
                    ("Error interno", "Enviar a reparar."),
                ]},
            ],
            "daily": [
                "Limpia el polvo y vuelve a colocar la cubierta antipolvo después de las verificaciones",
                "Elimina cualquier suciedad o cabello en los controles y los pies",
                "Si está doblada, agrietada o dañada, envíala a reparar",
                "Verifica el cero al inicio del día y antes de cada paciente",
            ],
            "weekly": [
                "Limpia el exterior con un paño húmedo y seca",
                "Limpia y luego vuelve a pintar cualquier metal expuesto u oxidado",
                "Aprieta cualquier tornillo flojo y verifica que las piezas estén bien ajustadas",
                "Verifica que la lectura sea precisa usando un peso conocido",
                "Envía a reparar si es inexacta o se traba",
                "Reemplaza la batería si la pantalla muestra batería baja",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "sphygmomanometer",
        "title": "Sphygmomanometers (B.P. sets)",
        "function": (
            "A sphygmomanometer is used to measure the patient's blood pressure. It consists of "
            "an inflatable cuff that is wrapped around the arm, an inflation device, and a "
            "manometer (mercury or aneroid) which indicates the pressure."
        ),
        "how_it_works": (
            "The cuff is wrapped around the patient's arm and inflated until the blood flow in "
            "the artery is interrupted. The air is then released slowly. The user listens with a "
            "stethoscope for the moment the arterial beats reappear (systolic pressure) and the "
            "moment they disappear (diastolic pressure). In mercury devices the pressure is "
            "indicated by the height of a column of mercury; in aneroid devices it is indicated "
            "by a needle on a calibrated dial."
        ),
        "faults": [
            {"fault": "Mercury leakage OR Mercury not at zero level", "cases": [
                ("Mercury leakage or overfilling", "Refer to technician for correction."),
            ]},
            {"fault": "Mercury is dirty", "cases": [
                ("Oxidation of mercury", "Refer to technician for cleaning."),
            ]},
            {"fault": "Pressure does not increase easily OR Pressure increases after inflation", "cases": [
                ("Valve or tube blockage", "Remove and clean all valves and tubes. Reassemble and test."),
            ]},
            {"fault": "Aneroid instrument does not return to zero", "cases": [
                ("Zero setting has moved", "Rotate collar on base until zero setting achieved and tighten. If still malfunctioning, refer to technician."),
            ]},
            {"fault": "Pressure does not remain steady", "cases": [
                ("Leakage of air", "Isolate leak by closing off parts of tubing. Replace leaking section and retest."),
            ]},
        ],
        "daily": [
            "Check equipment is safely packed",
            "If mercury is spilled, seal unit and send to technician",
            "Ensure all parts are present and are tightly fitted",
            "Check display is zero when cuff deflated",
            "Before use, check pressure rises and returns to zero",
        ],
        "weekly": [
            "Remove all dust and dirt with damp cloth or by hand",
            "Remove or replace any cracked rubber parts",
            "Check correct operation of inflation bulb and valves",
            "Remove any batteries if not in use for more than one month",
            "Inflate to 200 mmHg and check leakage is not faster than 2 mmHg in 10 seconds",
        ],
        "six_months": "Biomedical Technician check required. Check calibration of aneroid devices against mercury device.",
        "fr": {
            "title": "Tensiomètres (tensiomètres à mercure et anéroïdes)",
            "function": (
                "Un tensiomètre est utilisé pour mesurer la tension artérielle du patient. Il se "
                "compose d'un brassard gonflable qui est enroulé autour du bras, d'un dispositif de "
                "gonflage, et d'un manomètre (à mercure ou anéroïde) qui indique la pression."
            ),
            "how_it_works": (
                "Le brassard est enroulé autour du bras du patient et gonflé jusqu'à ce que "
                "l'afflux sanguin dans l'artère soit interrompu. L'air est ensuite libéré "
                "lentement. L'utilisateur écoute avec un stéthoscope le moment où les battements "
                "artériels réapparaissent (pression systolique) et le moment où ils disparaissent "
                "(pression diastolique). Dans les appareils à mercure, la pression est indiquée "
                "par la hauteur d'une colonne de mercure ; dans les appareils anéroïdes, elle est "
                "indiquée par une aiguille sur un cadran étalonné."
            ),
            "faults": [
                {"fault": "Fuite de mercure OU mercure pas au niveau zéro", "cases": [
                    ("Fuite ou sur-remplissage de mercure", "Adressez-vous au technicien pour correction."),
                ]},
                {"fault": "Le mercure est sale", "cases": [
                    ("Oxydation du mercure", "Adressez-vous au technicien pour nettoyage."),
                ]},
                {"fault": "La pression n'augmente pas facilement OU la pression augmente après le gonflage", "cases": [
                    ("Blocage de la vanne ou des tubes", "Retirez et nettoyez toutes les vannes et tubes. Remontez et testez."),
                ]},
                {"fault": "L'appareil anéroïde ne revient pas à zéro", "cases": [
                    ("Le réglage du zéro a bougé", "Faites pivoter le collier à la base jusqu'à obtenir le zéro, puis serrez. Si le dysfonctionnement persiste, adressez-vous au technicien."),
                ]},
                {"fault": "La pression ne reste pas stable", "cases": [
                    ("Fuite d'air", "Isolez la fuite en obturant des parties de la tubulure. Remplacez la section qui fuit et retestez."),
                ]},
            ],
            "daily": [
                "Vérifiez que l'équipement est rangé en toute sécurité",
                "En cas de déversement de mercure, scellez l'unité et envoyez-la au technicien",
                "Assurez-vous que toutes les pièces sont présentes et bien fixées",
                "Vérifiez que l'affichage est à zéro lorsque le brassard est dégonflé",
                "Avant utilisation, vérifiez que la pression monte et revient à zéro",
            ],
            "weekly": [
                "Retirez toute poussière et saleté avec un chiffon humide ou à la main",
                "Retirez ou remplacez toute pièce en caoutchouc fissurée",
                "Vérifiez le bon fonctionnement de la poire de gonflage et des vannes",
                "Retirez les piles si l'appareil n'est pas utilisé pendant plus d'un mois",
                "Gonflez à 200 mmHg et vérifiez que la fuite ne dépasse pas 2 mmHg en 10 secondes",
            ],
            "six_months": "Vérification par le technicien biomédical requise. Vérifiez l'étalonnage des appareils anéroïdes par rapport à un appareil à mercure.",
        },
        "es": {
            "title": "Esfigmomanómetros (tensiómetros)",
            "function": (
                "Un esfigmomanómetro se utiliza para medir la presión arterial del paciente. "
                "Consiste en un manguito inflable que se enrolla alrededor del brazo, un dispositivo "
                "de inflado y un manómetro (de mercurio o aneroide) que indica la presión."
            ),
            "how_it_works": (
                "El manguito se enrolla alrededor del brazo del paciente y se infla hasta que el "
                "flujo de sangre en la arteria se interrumpe. Luego el aire se libera lentamente. "
                "El usuario escucha con un estetoscopio el momento en que los latidos arteriales "
                "reaparecen (presión sistólica) y el momento en que desaparecen (presión "
                "diastólica). En los dispositivos de mercurio, la presión se indica por la altura "
                "de una columna de mercurio; en los dispositivos aneroides, se indica por una aguja "
                "en un dial calibrado."
            ),
            "faults": [
                {"fault": "Fuga de mercurio O mercurio no en el nivel cero", "cases": [
                    ("Fuga o sobrellenado de mercurio", "Consulta al técnico para su corrección."),
                ]},
                {"fault": "El mercurio está sucio", "cases": [
                    ("Oxidación del mercurio", "Consulta al técnico para su limpieza."),
                ]},
                {"fault": "La presión no aumenta fácilmente O la presión aumenta después del inflado", "cases": [
                    ("Bloqueo de la válvula o de los tubos", "Retira y limpia todas las válvulas y tubos. Vuelve a ensamblar y prueba."),
                ]},
                {"fault": "El instrumento aneroide no regresa a cero", "cases": [
                    ("El ajuste de cero se ha movido", "Rota el collar en la base hasta lograr el ajuste de cero y aprieta. Si aún falla, consulta al técnico."),
                ]},
                {"fault": "La presión no se mantiene estable", "cases": [
                    ("Fuga de aire", "Aísla la fuga cerrando partes del tubo. Reemplaza la sección que fuga y vuelve a probar."),
                ]},
            ],
            "daily": [
                "Verifica que el equipo esté guardado de forma segura",
                "Si se derrama mercurio, sella la unidad y envíala al técnico",
                "Asegúrate de que todas las piezas estén presentes y bien ajustadas",
                "Verifica que la pantalla esté en cero cuando el manguito está desinflado",
                "Antes del uso, verifica que la presión suba y regrese a cero",
            ],
            "weekly": [
                "Retira todo el polvo y la suciedad con un paño húmedo o a mano",
                "Retira o reemplaza cualquier pieza de goma agrietada",
                "Verifica el correcto funcionamiento de la pera de inflado y las válvulas",
                "Retira las baterías si no se va a usar por más de un mes",
                "Infla a 200 mmHg y verifica que la fuga no sea más rápida que 2 mmHg en 10 segundos",
            ],
            "six_months": "Se requiere la revisión del técnico biomédico. Verifica la calibración de los dispositivos aneroides contra el dispositivo de mercurio.",
        },
    },
    {
        "lang": "en",
        "slug": "stethoscope",
        "title": "Stethoscopes",
        "function": (
            "A stethoscope is used to listen to the internal sounds of the body, especially the "
            "heartbeat and breathing. It consists of a chestpiece (head) placed on the patient's "
            "skin, tubes connecting the chestpiece to the earpieces, and earpieces that are "
            "inserted into the user's ears."
        ),
        "how_it_works": (
            "The chestpiece has a diaphragm and a bell. When the diaphragm is placed on the "
            "patient's body, sounds are transmitted through the diaphragm, along the tubes, to "
            "the user's ears. The bell picks up low frequency sounds. The reliability of the "
            "stethoscope depends on the airtightness of all connections and the absence of "
            "blockages in the tubes."
        ),
        "faults": [
            {"fault": "Faint or no sound heard", "cases": [
                ("Leakage or blockage", "Remove all parts and check for leakage and blockage. Assemble and retest."),
            ]},
            {"fault": "Tube connector does not stay in headpiece", "cases": [
                ("Broken locking mechanism", "Refer to technician for repair."),
            ]},
            {"fault": "Parts damaged or faulty", "cases": [
                ("Broken part", "Replace with part taken from other units."),
            ]},
        ],
        "daily": [
            "Check equipment is safely packed",
            "Remove any dirt visible",
            "Check all parts are present and tightly fitted",
            "Tap gently before use to check operation",
        ],
        "weekly": [
            "Remove all dirt with damp cloth or by hand",
            "Remove earpieces and clean inside with warm water",
            "Remove or replace any cracked rubber parts",
            "Replace membrane if broken",
            "Check tube holder rotates easily within headpiece",
            "Check sound can be heard from both sides of headpiece",
        ],
        "fr": {
            "title": "Stéthoscopes",
            "function": (
                "Un stéthoscope est utilisé pour écouter les sons internes du corps, en particulier "
                "le rythme cardiaque et la respiration. Il se compose d'un pavillon (tête) placé "
                "sur la peau du patient, de tubes reliant le pavillon aux embouts auriculaires et "
                "d'embouts qui sont insérés dans les oreilles de l'utilisateur."
            ),
            "how_it_works": (
                "Le pavillon comporte une membrane et une cloche. Lorsque la membrane est placée "
                "sur le corps du patient, les sons sont transmis à travers la membrane, à travers "
                "les tubes, jusqu'aux oreilles de l'utilisateur. La cloche capte les sons à basse "
                "fréquence. La fiabilité du stéthoscope dépend de l'étanchéité de toutes les "
                "connexions et de l'absence de blocages dans les tubes."
            ),
            "faults": [
                {"fault": "Son faible ou absent", "cases": [
                    ("Fuite ou blocage", "Retirez toutes les pièces et vérifiez les fuites et blocages. Assemblez et retestez."),
                ]},
                {"fault": "Le connecteur du tube ne reste pas dans le pavillon", "cases": [
                    ("Mécanisme de verrouillage cassé", "Adressez-vous au technicien pour réparation."),
                ]},
                {"fault": "Pièces endommagées ou défectueuses", "cases": [
                    ("Pièce cassée", "Remplacez par une pièce prélevée sur d'autres unités."),
                ]},
            ],
            "daily": [
                "Vérifiez que l'équipement est rangé en toute sécurité",
                "Retirez toute saleté visible",
                "Vérifiez que toutes les pièces sont présentes et bien fixées",
                "Tapotez doucement avant utilisation pour vérifier le fonctionnement",
            ],
            "weekly": [
                "Retirez toute saleté avec un chiffon humide ou à la main",
                "Retirez les embouts et nettoyez l'intérieur avec de l'eau tiède",
                "Retirez ou remplacez toute pièce en caoutchouc fissurée",
                "Remplacez la membrane si elle est cassée",
                "Vérifiez que le support du tube pivote facilement dans le pavillon",
                "Vérifiez que le son peut être entendu des deux côtés du pavillon",
            ],
        },
        "es": {
            "title": "Estetoscopios",
            "function": (
                "Un estetoscopio se utiliza para escuchar los sonidos internos del cuerpo, "
                "especialmente los latidos del corazón y la respiración. Consiste en una campana "
                "(cabezal) que se coloca sobre la piel del paciente, tubos que conectan la campana "
                "con las olivas y olivas que se insertan en los oídos del usuario."
            ),
            "how_it_works": (
                "El cabezal consta de un diafragma y una campana. Cuando el diafragma se coloca "
                "sobre el cuerpo del paciente, los sonidos se transmiten a través del diafragma, a "
                "través de los tubos, hasta los oídos del usuario. La campana recoge los sonidos de "
                "baja frecuencia. La fiabilidad del estetoscopio depende de la estanqueidad de "
                "todas las conexiones y de la ausencia de obstrucciones en los tubos."
            ),
            "faults": [
                {"fault": "Se oye un sonido débil o no se oye", "cases": [
                    ("Fuga u obstrucción", "Retira todas las piezas y verifica si hay fugas y obstrucciones. Ensambla y vuelve a probar."),
                ]},
                {"fault": "El conector del tubo no se mantiene en el cabezal", "cases": [
                    ("Mecanismo de bloqueo roto", "Consulta al técnico para la reparación."),
                ]},
                {"fault": "Piezas dañadas o defectuosas", "cases": [
                    ("Pieza rota", "Reemplaza con una pieza tomada de otras unidades."),
                ]},
            ],
            "daily": [
                "Verifica que el equipo esté guardado de forma segura",
                "Retira cualquier suciedad visible",
                "Verifica que todas las piezas estén presentes y bien ajustadas",
                "Toca suavemente antes del uso para verificar el funcionamiento",
            ],
            "weekly": [
                "Retira toda la suciedad con un paño húmedo o a mano",
                "Retira las olivas y limpia el interior con agua tibia",
                "Retira o reemplaza cualquier pieza de goma agrietada",
                "Reemplaza la membrana si está rota",
                "Verifica que el soporte del tubo gire fácilmente dentro del cabezal",
                "Verifica que se escuche el sonido desde ambos lados del cabezal",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "suction_machine",
        "title": "Suction Machines",
        "function": (
            "A suction machine is used to remove blood, mucus and other secretions from the "
            "patient's airways and other cavities. The device creates a negative pressure that "
            "draws the fluids into a collection bottle."
        ),
        "how_it_works": (
            "A pump or compressor creates the suction through tubing connected to a collection "
            "bottle. The patient is connected to the bottle by a tube, and fluids are drawn into "
            "the bottle. A pressure gauge and a control valve allow the level of vacuum to be "
            "regulated. Some units have a manual backup suction by pedal or hand pump."
        ),
        "faults": [
            {"fault": "Machine is not running", "cases": [
                ("No power from mains socket. Fuse blown", "Check power switch is on. Check mains power is present at socket using equipment known to be working. Contact electrician for rewiring if power not present. Check for leaks or wire causing fuse to blow and correct this. Replace fuse with correct voltage and current rating. Test operation."),
                ("Electrical cable fault", "Try cable on another piece of equipment. Contact electrician for repair if required."),
                ("Internal wiring or switch fault", "Refer to electrician."),
            ]},
            {"fault": "Poor fluid flow, pressure gauge low", "cases": [
                ("Tube / seal / bottle leaking or disconnected", "Close different tubes by bending. When pressure gauge changes, leakage point has been passed. Replace damaged tube or seal."),
                ("Air outlet valve blocked", "Clean outlet valve."),
                ("Control valve stuck", "Operate control valve through full range. Send for repair if stuck."),
                ("Internal or control error", "Refer to technician."),
            ]},
            {"fault": "Poor fluid flow, pressure gauge high", "cases": [
                ("Blocked filter or tube", "Disconnect each tube one at a time. When air flow is stopped, blockage has been passed. Replace filter or unblock tube."),
            ]},
            {"fault": "Filter discoloured", "cases": [
                ("Floating valve broken", "Change filter, clean or replace floating valve."),
            ]},
            {"fault": "Electrical shocks", "cases": [
                ("Wiring fault", "Refer to electrician."),
            ]},
            {"fault": "Manual suction is jammed", "cases": [
                ("Internal slider stuck", "Refer to technician for greasing."),
            ]},
        ],
        "daily": [
            "Wipe dust off exterior and cover equipment after checks",
            "Wash bottle and patient tubing with sterilising solution",
            "Check all fittings and accessories are mounted correctly",
            "Check filter is clean",
            "If in use that day, run a brief function check before clinic",
        ],
        "weekly": [
            "Unplug, clean outside with damp cloth and dry off",
            "Wipe round bottle seal with damp cloth, replace if cracked",
            "Remove dirt from wheels / moving parts",
            "Check parts are fitted tightly and replace any cracked tubes",
            "Check mains plug screws are tight",
            "Check mains cable has no bare wire and is not damaged",
            "Check all switches and vacuum control operate correctly",
        ],
        "fr": {
            "title": "Appareils d'aspiration",
            "function": (
                "Un appareil d'aspiration est utilisé pour évacuer le sang, le mucus et d'autres "
                "sécrétions des voies respiratoires et autres cavités du patient. Le dispositif "
                "crée une pression négative qui aspire les fluides dans une bouteille de "
                "collecte."
            ),
            "how_it_works": (
                "Une pompe ou un compresseur crée une aspiration par l'intermédiaire d'une "
                "tubulure reliée à une bouteille de collecte. Le patient est raccordé à la "
                "bouteille par une tubulure, et les fluides sont aspirés dans la bouteille. Un "
                "manomètre et une vanne de réglage permettent de contrôler le niveau de vide. "
                "Certaines unités disposent d'une aspiration manuelle de secours par pédale ou "
                "pompe à main."
            ),
            "faults": [
                {"fault": "La machine ne fonctionne pas", "cases": [
                    ("Pas de courant à la prise secteur. Fusible grillé", "Vérifiez que l'interrupteur est allumé. Vérifiez que le courant est présent à la prise à l'aide d'un équipement connu en état de marche. Contactez un électricien pour le câblage si le courant n'est pas présent. Vérifiez s'il n'y a pas de fuites ou de fils provoquant la fusion du fusible et corrigez. Remplacez le fusible par un fusible de tension et de courant corrects. Testez le fonctionnement."),
                    ("Défaut de câble électrique", "Essayez le câble sur un autre équipement. Contactez un électricien pour réparation si nécessaire."),
                    ("Défaut de câblage interne ou d'interrupteur", "Adressez-vous à l'électricien."),
                ]},
                {"fault": "Mauvais écoulement des fluides, manomètre bas", "cases": [
                    ("Tube / joint / bouteille qui fuit ou déconnecté", "Fermez différents tubes en les pliant. Lorsque le manomètre change, le point de fuite a été dépassé. Remplacez le tube ou le joint endommagé."),
                    ("Évent d'air bloqué", "Nettoyez l'évent."),
                    ("Van de réglage bloquée", "Actionnez la vanne de réglage sur toute sa plage. Envoyez pour réparation si elle est bloquée."),
                    ("Erreur interne ou de commande", "Adressez-vous au technicien."),
                ]},
                {"fault": "Mauvais écoulement des fluides, manomètre haut", "cases": [
                    ("Filtre ou tube bloqué", "Débranchez chaque tube un par un. Lorsque le flux d'air s'arrête, le blocage a été dépassé. Remplacez le filtre ou débloquez le tube."),
                ]},
                {"fault": "Filtre décoloré", "cases": [
                    ("Vanne flottante cassée", "Changez le filtre, nettoyez ou remplacez la vanne flottante."),
                ]},
                {"fault": "Chocs électriques", "cases": [
                    ("Défaut de câblage", "Adressez-vous à l'électricien."),
                ]},
                {"fault": "L'aspiration manuelle est bloquée", "cases": [
                    ("Coulisseau interne bloqué", "Adressez-vous au technicien pour graissage."),
                ]},
            ],
            "daily": [
                "Essuyez la poussière de l'extérieur et couvrez l'équipement après les vérifications",
                "Lavez la bouteille et la tubulure du patient avec une solution stérilisante",
                "Vérifiez que tous les raccords et accessoires sont montés correctement",
                "Vérifiez que le filtre est propre",
                "Si l'appareil est utilisé ce jour-là, effectuez un bref contrôle de fonctionnement avant la consultation",
            ],
            "weekly": [
                "Débranchez, nettoyez l'extérieur avec un chiffon humide et séchez",
                "Essuyez le joint de la bouteille avec un chiffon humide, remplacez-le s'il est fissuré",
                "Retirez la saleté des roues / pièces mobiles",
                "Vérifiez que les pièces sont bien fixées et remplacez les tubes fissurés",
                "Vérifiez que les vis de la fiche secteur sont serrées",
                "Vérifiez que le câble secteur n'a pas de fil nu et n'est pas endommagé",
                "Vérifiez que tous les interrupteurs et la commande de vide fonctionnent correctement",
            ],
        },
        "es": {
            "title": "Máquinas de succión",
            "function": (
                "Una máquina de succión se utiliza para extraer sangre, moco y otras secreciones de "
                "las vías respiratorias y otras cavidades del paciente. El dispositivo crea una "
                "presión negativa que aspira los fluidos hacia una botella de recolección."
            ),
            "how_it_works": (
                "Una bomba o compresor crea la succión a través de un tubo conectado a una botella "
                "de recolección. El paciente se conecta a la botella mediante un tubo y los fluidos "
                "se aspiran hacia la botella. Un manómetro y una válvula de control permiten "
                "regular el nivel de vacío. Algunas unidades tienen una succión manual de respaldo "
                "mediante pedal o bomba de mano."
            ),
            "faults": [
                {"fault": "La máquina no funciona", "cases": [
                    ("No hay corriente en la toma de red. Fusible fundido", "Verifica que el interruptor esté encendido. Comprueba que la toma tenga corriente usando un equipo que se sepa que funciona. Contacta a un electricista para el cableado si no hay corriente. Verifica si hay fugas o cables que causen que el fusible se funda y corrígelo. Reemplaza el fusible con la tensión y corriente correctas. Prueba el funcionamiento."),
                    ("Fallo del cable eléctrico", "Prueba el cable en otro equipo. Contacta a un electricista para su reparación si es necesario."),
                    ("Fallo del cableado interno o del interruptor", "Consulta al electricista."),
                ]},
                {"fault": "Flujo de fluidos deficiente, manómetro bajo", "cases": [
                    ("Tubo / sello / botella con fugas o desconectado", "Cierra diferentes tubos doblándolos. Cuando el manómetro cambie, se ha pasado el punto de fuga. Reemplaza el tubo o sello dañado."),
                    ("La válvula de salida de aire está bloqueada", "Limpia la válvula de salida."),
                    ("Válvula de control atascada", "Opera la válvula de control en todo su rango. Envía a reparar si está atascada."),
                    ("Error interno o de control", "Consulta al técnico."),
                ]},
                {"fault": "Flujo de fluidos deficiente, manómetro alto", "cases": [
                    ("Filtro o tubo bloqueado", "Desconecta cada tubo uno a la vez. Cuando el flujo de aire se detenga, se ha pasado el bloqueo. Reemplaza el filtro o desbloquea el tubo."),
                ]},
                {"fault": "Filtro descolorido", "cases": [
                    ("Válvula flotante rota", "Cambia el filtro, limpia o reemplaza la válvula flotante."),
                ]},
                {"fault": "Descargas eléctricas", "cases": [
                    ("Fallo del cableado", "Consulta al electricista."),
                ]},
                {"fault": "La succión manual está atascada", "cases": [
                    ("Deslizador interno atascado", "Consulta al técnico para la lubricación."),
                ]},
            ],
            "daily": [
                "Limpia el polvo del exterior y cubre el equipo después de las verificaciones",
                "Lava la botella y el tubo del paciente con solución esterilizante",
                "Verifica que todos los accesorios y accesorios estén montados correctamente",
                "Verifica que el filtro esté limpio",
                "Si se usará ese día, realiza una breve verificación de funcionamiento antes de la consulta",
            ],
            "weekly": [
                "Desenchufa, limpia el exterior con un paño húmedo y seca",
                "Limpia el sello de la botella con un paño húmedo, reemplázalo si está agrietado",
                "Retira la suciedad de las ruedas / piezas móviles",
                "Verifica que las piezas estén bien ajustadas y reemplaza cualquier tubo agrietado",
                "Verifica que los tornillos del enchufe estén apretados",
                "Verifica que el cable de red no tenga cable pelado y no esté dañado",
                "Verifica que todos los interruptores y el control de vacío funcionen correctamente",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "operating_table",
        "title": "Operating Theatre and Delivery Tables",
        "function": (
            "Operating theatre and delivery tables support the patient during surgical "
            "procedures and childbirth. They allow the patient's position and exposure to be "
            "adjusted according to the needs of the procedure. Some tables are electrically "
            "driven, others are hydraulic or manual."
        ),
        "how_it_works": (
            "The tables consist of an adjustable top mounted on a base with castors and brakes. "
            "The sections of the top (backrest, legs, etc.) are adjusted using levers or "
            "controls. Electric tables use motors; hydraulic tables use hydraulic jacks. Movement "
            "is controlled by levers or buttons depending on the type of table."
        ),
        "faults": [
            {"fault": "Table cannot be relocated", "cases": [
                ("Wheels jammed", "Clean wheels, remove obstruction."),
                ("Electric motor not operational (electrically driven table)", "Check power to table. Replace fuse if blown. If problem persists, refer to technician."),
            ]},
            {"fault": "Table section or body cannot be moved", "cases": [
                ("Lock or lever is jammed", "Clean jammed part, remove rust and dirt, lightly oil and replace."),
                ("No power to electric table", "Check correct switch is used. Check power and fuses."),
                ("No oil in hydraulic table", "Refill hydraulic oil if needed. Check no leakage occurs."),
            ]},
            {"fault": "Oil leakage from hydraulic table", "cases": [
                ("Oil leakage", "Locate leak and block it. Clear spillage. Refer to technician."),
            ]},
            {"fault": "Electric shocks", "cases": [
                ("Wiring fault", "Refer to technician immediately."),
            ]},
        ],
        "daily": [
            "Clean, dry and disinfect all parts",
            "Remove all paper, tape and foreign matter",
            "Check all parts are present and tightly fitted",
            "Replace mattress if worn or damaged",
            "Check no oil is leaking from hydraulics",
            "Check essential movements before use",
        ],
        "weekly": [
            "Clean and dry table, base and underneath table and base",
            "Wipe off any escaped oil or grease from joints",
            "Fully inspect mattress and table for signs of wear",
            "Replace any worn items and send for repair",
            "Check wheel brakes function and wheels rotate",
            "Ensure all moving parts can move, applying grease if needed",
        ],
        "fr": {
            "title": "Tables d'opération et tables d'accouchement",
            "function": (
                "Les tables d'opération et d'accouchement supportent le patient pendant les "
                "interventions chirurgicales et les accouchements. Elles permettent d'ajuster la "
                "position du patient et de l'exposer selon les besoins de la procédure. Certaines "
                "tables sont entraînées électriquement, d'autres sont hydrauliques ou manuelles."
            ),
            "how_it_works": (
                "Les tables se composent d'un plateau réglable monté sur un socle à roulettes "
                "avec freins. Les sections du plateau (dossier, jambes, etc.) sont réglées à "
                "l'aide de leviers ou de commandes. Les tables électriques utilisent des moteurs ; "
                "les tables hydrauliques utilisent des vérins hydrauliques. Le mouvement est "
                "contrôlé par des leviers ou des boutons selon le type de table."
            ),
            "faults": [
                {"fault": "La table ne peut pas être déplacée", "cases": [
                    ("Roues bloquées", "Nettoyez les roues, retirez l'obstruction."),
                    ("Moteur électrique non opérationnel (table à entraînement électrique)", "Vérifiez l'alimentation de la table. Remplacez le fusible s'il a sauté. Si le problème persiste, adressez-vous au technicien."),
                ]},
                {"fault": "Une section de la table ou le corps ne peut pas être déplacé(e)", "cases": [
                    ("Verrou ou levier bloqué", "Nettoyez la pièce bloquée, retirez la rouille et la saleté, huilez légèrement et remplacez."),
                    ("Pas d'alimentation pour la table électrique", "Vérifiez que le bon interrupteur est utilisé. Vérifiez l'alimentation et les fusibles."),
                    ("Pas d'huile dans la table hydraulique", "Remplissez l'huile hydraulique si nécessaire. Vérifiez qu'aucune fuite ne se produit."),
                ]},
                {"fault": "Fuite d'huile de la table hydraulique", "cases": [
                    ("Fuite d'huile", "Localisez la fuite et bloquez-la. Éliminez tout déversement. Adressez-vous au technicien."),
                ]},
                {"fault": "Chocs électriques", "cases": [
                    ("Défaut de câblage", "Adressez-vous immédiatement au technicien."),
                ]},
            ],
            "daily": [
                "Nettoyez, séchez et désinfectez toutes les pièces",
                "Retirez tout papier, ruban adhésif et corps étranger",
                "Vérifiez que toutes les pièces sont présentes et bien fixées",
                "Remplacez le matelas s'il est usé ou endommagé",
                "Vérifiez qu'aucune huile ne fuit de l'hydraulique",
                "Vérifiez les mouvements essentiels avant utilisation",
            ],
            "weekly": [
                "Nettoyez et séchez la table, le socle, et le dessous de la table et du socle",
                "Essuyez toute huile ou graisse échappée des joints",
                "Inspectez complètement le matelas et la table pour détecter des signes d'usure",
                "Remplacez les articles usés et envoyez pour réparation",
                "Vérifiez que les freins des roues fonctionnent et que les roues tournent",
                "Assurez-vous que toutes les pièces mobiles peuvent bouger, en appliquant de la graisse si nécessaire",
            ],
        },
        "es": {
            "title": "Mesas de operación y de parto",
            "function": (
                "Las mesas de operación y de parto sostienen al paciente durante las "
                "intervenciones quirúrgicas y los partos. Permiten ajustar la posición del "
                "paciente y la exposición según las necesidades del procedimiento. Algunas mesas "
                "son eléctricas, otras son hidráulicas o manuales."
            ),
            "how_it_works": (
                "Las mesas constan de una superficie ajustable montada sobre una base con ruedas y "
                "frenos. Las secciones de la superficie (respaldo, piernas, etc.) se ajustan con "
                "palancas o controles. Las mesas eléctricas utilizan motores; las mesas hidráulicas "
                "utilizan gatos hidráulicos. El movimiento se controla con palancas o botones según "
                "el tipo de mesa."
            ),
            "faults": [
                {"fault": "La mesa no puede reubicarse", "cases": [
                    ("Ruedas atascadas", "Limpia las ruedas, retira la obstrucción."),
                    ("Motor eléctrico no operativo (mesa eléctrica)", "Verifica la corriente de la mesa. Reemplaza el fusible si se ha fundido. Si el problema persiste, consulta al técnico."),
                ]},
                {"fault": "La sección o el cuerpo de la mesa no puede moverse", "cases": [
                    ("El seguro o la palanca están atascados", "Limpia la pieza atascada, retira óxido y suciedad, aceita ligeramente y reemplaza."),
                    ("Sin corriente en la mesa eléctrica", "Verifica que se use el interruptor correcto. Verifica la corriente y los fusibles."),
                    ("Sin aceite en la mesa hidráulica", "Rellena el aceite hidráulico si es necesario. Verifica que no ocurran fugas."),
                ]},
                {"fault": "Fuga de aceite de la mesa hidráulica", "cases": [
                    ("Fuga de aceite", "Localiza la fuga y bloquéala. Limpia el derrame. Consulta al técnico."),
                ]},
                {"fault": "Descargas eléctricas", "cases": [
                    ("Fallo del cableado", "Consulta inmediatamente al técnico."),
                ]},
            ],
            "daily": [
                "Limpia, seca y desinfecta todas las piezas",
                "Retira todo el papel, cinta y materia extraña",
                "Verifica que todas las piezas estén presentes y bien ajustadas",
                "Reemplaza el colchón si está desgastado o dañado",
                "Verifica que no haya fugas de aceite de la hidráulica",
                "Verifica los movimientos esenciales antes del uso",
            ],
            "weekly": [
                "Limpia y seca la mesa, la base y la parte inferior de la mesa y la base",
                "Limpia cualquier aceite o grasa que haya escapado de las juntas",
                "Inspecciona completamente el colchón y la mesa para detectar signos de desgaste",
                "Reemplaza cualquier artículo desgastado y envía a reparar",
                "Verifica que los frenos de las ruedas funcionen y que las ruedas giren",
                "Asegúrate de que todas las piezas móviles puedan moverse, aplicando grasa si es necesario",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "ultrasound_machine",
        "title": "Ultrasound Machines",
        "function": (
            "An ultrasound machine uses high-frequency sound waves to produce images of the "
            "internal organs of the body. The ultrasound examination is used to examine internal "
            "organs, monitor a pregnancy and guide certain medical procedures."
        ),
        "how_it_works": (
            "A probe (transducer) is placed on the patient's skin after applying ultrasound gel "
            "to ensure good contact. The probe emits high-frequency sound waves which penetrate "
            "the body and are reflected off the tissues. The echoes are detected at the probe and "
            "converted by the machine's computer into an image displayed on the screen. Dense "
            "tissues produce stronger echoes than soft tissues."
        ),
        "faults": [
            {"fault": "Equipment is not running", "cases": [
                ("No power from mains socket. Electrical cable fault", "Check power switch is on. Replace fuse with correct voltage and current if blown. Check mains power is present at socket using equipment known to be working. Contact electrician for rewiring if power not present. Try cable on another piece of equipment. Contact electrician for repair if required."),
            ]},
            {"fault": "Fuse keeps blowing", "cases": [
                ("Power supply or cable fault", "Refer to electrician."),
            ]},
            {"fault": "Probe head damaged or noisy", "cases": [
                ("Possible internal fault", "Exchange probe. Send for testing and repair."),
            ]},
            {"fault": "Image quality poor", "cases": [
                ("Gel insufficient", "Use more ultrasound gel."),
                ("Controls set incorrectly", "Check controls for correct positioning and operation (refer to user manual)."),
                ("Mains voltage is too low", "Use voltage stabiliser."),
                ("Probe / display problem", "Refer to biomedical technician."),
            ]},
            {"fault": "Display / computer error", "cases": [
                ("Software fault", "Turn machine off and restart. If problem persists, refer to biomedical technician."),
            ]},
            {"fault": "Electrical shocks", "cases": [
                ("Wiring fault", "Refer to electrician."),
            ]},
        ],
        "daily": [
            "Wipe dust off exterior and cover equipment after checks",
            "Remove any tape, paper or foreign body from equipment",
            "Wipe probe with alcohol-free tissue or cloth",
            "Check all fittings and accessories are mounted correctly",
            "Check cables are not twisted and probe is safely stored",
            "If in use that day, run a brief function check before clinic",
        ],
        "weekly": [
            "Unplug, clean outside / wheels / rear with damp cloth, dry off",
            "Remove, clean and dry external filter if present",
            "Check mains plug screws are tight",
            "Check mains cable has no bare wire and is not damaged",
            "If machine has not been in use, run and test briefly",
        ],
        "fr": {
            "title": "Échographes",
            "function": (
                "Un échographe utilise des ondes sonores à haute fréquence pour produire des "
                "images des organes internes du corps. L'examen échographique est utilisé pour "
                "examiner les organes internes, surveiller une grossesse et orienter certains "
                "gestes médicaux."
            ),
            "how_it_works": (
                "Une sonde (transducteur) est placée sur la peau du patient après application d'un "
                "gel d'échographie pour assurer un bon contact. La sonde émet des ondes sonores à "
                "haute fréquence qui pénètrent le corps et se réfléchissent sur les tissus. Les "
                "échos sont détectés par la sonde et convertis par l'ordinateur de la machine en "
                "une image affichée à l'écran. Les tissus denses produisent des échos plus "
                "intenses que les tissus mous."
            ),
            "faults": [
                {"fault": "L'équipement ne fonctionne pas", "cases": [
                    ("Pas de courant à la prise secteur. Défaut de câble électrique", "Vérifiez que l'interrupteur est allumé. Remplacez le fusible par un fusible de tension et de courant corrects s'il a sauté. Vérifiez que le courant est présent à la prise à l'aide d'un équipement connu en état de marche. Contactez un électricien pour le câblage si le courant n'est pas présent. Essayez le câble sur un autre équipement. Contactez un électricien pour réparation si nécessaire."),
                ]},
                {"fault": "Le fusible saute constamment", "cases": [
                    ("Défaut d'alimentation ou de câble", "Adressez-vous à l'électricien."),
                ]},
                {"fault": "Tête de sonde endommagée ou bruyante", "cases": [
                    ("Défaut interne possible", "Échangez la sonde. Envoyez pour test et réparation."),
                ]},
                {"fault": "Qualité d'image médiocre", "cases": [
                    ("Gel insuffisant", "Utilisez davantage de gel d'échographie."),
                    ("Commandes mal réglées", "Vérifiez la position et le fonctionnement des commandes (voir le manuel d'utilisation)."),
                    ("Tension du secteur trop basse", "Utilisez un stabilisateur de tension."),
                    ("Problème de sonde / d'affichage", "Adressez-vous au technicien biomédical."),
                ]},
                {"fault": "Erreur d'affichage / d'ordinateur", "cases": [
                    ("Défaut logiciel", "Éteignez la machine et redémarrez. Si le problème persiste, adressez-vous au technicien biomédical."),
                ]},
                {"fault": "Chocs électriques", "cases": [
                    ("Défaut de câblage", "Adressez-vous à l'électricien."),
                ]},
            ],
            "daily": [
                "Essuyez la poussière de l'extérieur et couvrez l'équipement après les vérifications",
                "Retirez tout ruban adhésif, papier ou corps étranger de l'équipement",
                "Essuyez la sonde avec une lingette ou un chiffon sans alcool",
                "Vérifiez que tous les raccords et accessoires sont montés correctement",
                "Vérifiez que les câbles ne sont pas entortillés et que la sonde est rangée en toute sécurité",
                "Si l'appareil est utilisé ce jour-là, effectuez un bref contrôle de fonctionnement avant la consultation",
            ],
            "weekly": [
                "Débranchez, nettoyez l'extérieur / les roues / l'arrière avec un chiffon humide, séchez",
                "Retirez, nettoyez et séchez le filtre externe s'il existe",
                "Vérifiez que les vis de la fiche secteur sont serrées",
                "Vérifiez que le câble secteur n'a pas de fil nu et n'est pas endommagé",
                "Si la machine n'a pas été utilisée, faites-la fonctionner et testez-la brièvement",
            ],
        },
        "es": {
            "title": "Máquinas de ultrasonido",
            "function": (
                "Una máquina de ultrasonido utiliza ondas sonoras de alta frecuencia para producir "
                "imágenes de los órganos internos del cuerpo. El examen de ultrasonido se utiliza "
                "para examinar órganos internos, controlar un embarazo y guiar ciertos "
                "procedimientos médicos."
            ),
            "how_it_works": (
                "Una sonda (transductor) se coloca sobre la piel del paciente después de aplicar "
                "gel de ultrasonido para asegurar un buen contacto. La sonda emite ondas sonoras de "
                "alta frecuencia que penetran el cuerpo y se reflejan en los tejidos. Los ecos se "
                "detectan en la sonda y la computadora de la máquina los convierte en una imagen "
                "mostrada en la pantalla. Los tejidos densos producen ecos más intensos que los "
                "tejidos blandos."
            ),
            "faults": [
                {"fault": "El equipo no funciona", "cases": [
                    ("No hay corriente en la toma de red. Fallo del cable eléctrico", "Verifica que el interruptor esté encendido. Reemplaza el fusible con la tensión y corriente correctas si se ha fundido. Comprueba que la toma tenga corriente usando un equipo que se sepa que funciona. Contacta a un electricista para el cableado si no hay corriente. Prueba el cable en otro equipo. Contacta a un electricista para su reparación si es necesario."),
                ]},
                {"fault": "El fusible se sigue fundiendo", "cases": [
                    ("Fallo de la fuente de alimentación o del cable", "Consulta al electricista."),
                ]},
                {"fault": "Cabezal de la sonda dañado o ruidoso", "cases": [
                    ("Posible fallo interno", "Cambia la sonda. Envía a prueba y reparación."),
                ]},
                {"fault": "Calidad de imagen deficiente", "cases": [
                    ("Gel insuficiente", "Usa más gel de ultrasonido."),
                    ("Controles configurados incorrectamente", "Verifica los controles para su correcta posición y funcionamiento (consulta el manual del usuario)."),
                    ("La tensión de red es demasiado baja", "Usa un estabilizador de voltaje."),
                    ("Problema de sonda / pantalla", "Consulta al técnico biomédico."),
                ]},
                {"fault": "Error de pantalla / computadora", "cases": [
                    ("Fallo del software", "Apaga la máquina y reiníciala. Si el problema persiste, consulta al técnico biomédico."),
                ]},
                {"fault": "Descargas eléctricas", "cases": [
                    ("Fallo del cableado", "Consulta al electricista."),
                ]},
            ],
            "daily": [
                "Limpia el polvo del exterior y cubre el equipo después de las verificaciones",
                "Retira cualquier cinta, papel o cuerpo extraño del equipo",
                "Limpia la sonda con una toallita o paño sin alcohol",
                "Verifica que todos los accesorios y accesorios estén montados correctamente",
                "Verifica que los cables no estén retorcidos y que la sonda esté guardada de forma segura",
                "Si se usará ese día, realiza una breve verificación de funcionamiento antes de la consulta",
            ],
            "weekly": [
                "Desenchufa, limpia el exterior / ruedas / parte trasera con un paño húmedo y seca",
                "Retira, limpia y seca el filtro externo si existe",
                "Verifica que los tornillos del enchufe estén apretados",
                "Verifica que el cable de red no tenga cable pelado y no esté dañado",
                "Si la máquina no ha estado en uso, hazla funcionar y pruébala brevemente",
            ],
        },
    },
    {
        "lang": "en",
        "slug": "xray_machine",
        "title": "X-Ray Machines",
        "function": (
            "An X-ray machine uses X-rays to produce images of the internal structures of the "
            "body. The X-ray examination is used to diagnose fractures, infections and other "
            "medical conditions."
        ),
        "how_it_works": (
            "The X-ray tube generates X-rays that pass through the patient's body. Dense "
            "tissues, such as bones, absorb more X-rays than soft tissues. The rays that pass "
            "through the body are detected on a film or a digital detector, producing an image "
            "where dense tissues appear light and soft tissues appear darker. Technicians wear "
            "lead aprons and use collimators to limit radiation exposure."
        ),
        "faults": [
            {"fault": "X-Ray unit does not switch on", "cases": [
                ("Mains power not connected", "Check the machine is plugged into the mains socket and that all switches are on. Replace fuse with correct voltage and current if blown. Check mains power is present at socket using equipment known to be working. Contact electrician for rewiring if power not present."),
            ]},
            {"fault": "X-Ray machine not exposing, even when power is on", "cases": [
                ("Safety interlock is on. Exposure switch cable problem. Internal error", "Check safety locks, all switches. Check for any loose connection. Refer to biomedical technician."),
            ]},
            {"fault": "Poor X-Ray image quality", "cases": [
                ("X-Ray tube problem", "Refer to biomedical technician / medical physicist."),
            ]},
            {"fault": "The table does not move", "cases": [
                ("Table motor or cable problem. Safety switch or fuse problem", "Check all cable connections. Check relevant fuse or switch."),
                ("Control circuit problem", "Refer to biomedical technician."),
            ]},
            {"fault": "Electrical shocks", "cases": [
                ("Wiring fault", "Refer to biomedical technician immediately."),
            ]},
        ],
        "daily": [
            "Clean dust from the unit with a dry cloth",
            "Remove any tape, paper or foreign body from equipment",
            "Check all parts are present and connected",
            "Check cables are not twisted and remove from service if any damage is visible",
            "Switch on power and check all indicators function",
        ],
        "weekly": [
            "Clean all dust and dirt from the X-Ray machine and room",
            "If any plug, cable or socket is damaged, refer to biomedical technician",
            "Check all knobs, switches and wheels operate properly",
            "Check lead aprons for any defects",
            "Check table, cassette holder and grids for smooth movement",
            "If machine has not been in use, wear lead apron and check whether exposure indicator lights on switch operation",
            "Check collimator bulb, replace with correct type if needed",
        ],
        "fr": {
            "title": "Appareils de radiographie (rayons X)",
            "function": (
                "Un appareil de radiographie utilise des rayons X pour produire des images des "
                "structures internes du corps. L'examen radiographique est utilisé pour "
                "diagnostiquer des fractures, des infections et d'autres conditions médicales."
            ),
            "how_it_works": (
                "Le tube à rayons X génère des rayons X qui traversent le corps du patient. Les "
                "tissus denses, comme les os, absorbent davantage de rayons X que les tissus mous. "
                "Les rayons qui traversent le corps sont détectés par un film ou un détecteur "
                "numérique, produisant une image où les tissus denses apparaissent clairs et les "
                "tissus mous plus sombres. Les techniciens portent des tabliers de plomb et "
                "utilisent des collimateurs pour limiter l'exposition aux rayonnements."
            ),
            "faults": [
                {"fault": "L'unité de radiographie ne s'allume pas", "cases": [
                    ("Alimentation secteur non connectée", "Vérifiez que la machine est branchée à la prise secteur et que tous les interrupteurs sont allumés. Remplacez le fusible par un fusible de tension et de courant corrects s'il a sauté. Vérifiez que le courant est présent à la prise à l'aide d'un équipement connu en état de marche. Contactez un électricien pour le câblage si le courant n'est pas présent."),
                ]},
                {"fault": "La machine ne produit pas d'exposition, même sous tension", "cases": [
                    ("Interverrouillage de sécurité activé. Problème de câble de l'interrupteur d'exposition. Erreur interne", "Vérifiez les verrous de sécurité et tous les interrupteurs. Vérifiez toute connexion desserrée. Adressez-vous au technicien biomédical."),
                ]},
                {"fault": "Qualité d'image radiographique médiocre", "cases": [
                    ("Problème de tube à rayons X", "Adressez-vous au technicien biomédical / physicien médical."),
                ]},
                {"fault": "La table ne bouge pas", "cases": [
                    ("Problème de moteur ou de câble de la table. Problème d'interrupteur de sécurité ou de fusible", "Vérifiez toutes les connexions de câbles. Vérifiez le fusible ou l'interrupteur concerné."),
                    ("Problème de circuit de commande", "Adressez-vous au technicien biomédical."),
                ]},
                {"fault": "Chocs électriques", "cases": [
                    ("Défaut de câblage", "Adressez-vous immédiatement au technicien biomédical."),
                ]},
            ],
            "daily": [
                "Nettoyez la poussière de l'unité avec un chiffon sec",
                "Retirez tout ruban adhésif, papier ou corps étranger de l'équipement",
                "Vérifiez que toutes les pièces sont présentes et connectées",
                "Vérifiez que les câbles ne sont pas entortillés et retirez du service tout câble présentant des dommages visibles",
                "Allumez l'appareil et vérifiez que tous les indicateurs fonctionnent",
            ],
            "weekly": [
                "Nettoyez toute la poussière et la saleté de l'appareil de radiographie et de la salle",
                "Si une fiche, un câble ou une prise est endommagé, adressez-vous au technicien biomédical",
                "Vérifiez que tous les boutons, interrupteurs et roues fonctionnent correctement",
                "Vérifiez que les tabliers de plomb ne présentent aucun défaut",
                "Vérifiez le mouvement fluide de la table, du porte-cassette et des grilles",
                "Si la machine n'a pas été utilisée, portez un tablier de plomb et vérifiez que le voyant d'exposition s'allume lors de l'actionnement de l'interrupteur",
                "Vérifiez l'ampoule du collimateur, remplacez-la par le type correct si nécessaire",
            ],
        },
        "es": {
            "title": "Máquinas de rayos X",
            "function": (
                "Una máquina de rayos X utiliza rayos X para producir imágenes de las estructuras "
                "internas del cuerpo. El examen de rayos X se utiliza para diagnosticar fracturas, "
                "infecciones y otras afecciones médicas."
            ),
            "how_it_works": (
                "El tubo de rayos X genera rayos X que atraviesan el cuerpo del paciente. Los "
                "tejidos densos, como los huesos, absorben más rayos X que los tejidos blandos. Los "
                "rayos que atraviesan el cuerpo se detectan en una película o un detector digital, "
                "produciendo una imagen donde los tejidos densos aparecen claros y los tejidos "
                "blandos más oscuros. Los técnicos usan delantales de plomo y collimadores para "
                "limitar la exposición a la radiación."
            ),
            "faults": [
                {"fault": "La unidad de rayos X no enciende", "cases": [
                    ("Corriente de red no conectada", "Verifica que la máquina esté enchufada a la toma de red y que todos los interruptores estén encendidos. Reemplaza el fusible con la tensión y corriente correctas si se ha fundido. Comprueba que la toma tenga corriente usando un equipo que se sepa que funciona. Contacta a un electricista para el cableado si no hay corriente."),
                ]},
                {"fault": "La máquina de rayos X no expone, incluso con corriente", "cases": [
                    ("El interbloqueo de seguridad está activado. Problema en el cable del interruptor de exposición. Error interno", "Verifica las cerraduras de seguridad y todos los interruptores. Verifica cualquier conexión floja. Consulta al técnico biomédico."),
                ]},
                {"fault": "Mala calidad de imagen de rayos X", "cases": [
                    ("Problema del tubo de rayos X", "Consulta al técnico biomédico / físico médico."),
                ]},
                {"fault": "La mesa no se mueve", "cases": [
                    ("Problema del motor o del cable de la mesa. Problema del interruptor de seguridad o del fusible", "Verifica todas las conexiones de cables. Verifica el fusible o interruptor correspondiente."),
                    ("Problema del circuito de control", "Consulta al técnico biomédico."),
                ]},
                {"fault": "Descargas eléctricas", "cases": [
                    ("Fallo del cableado", "Consulta inmediatamente al técnico biomédico."),
                ]},
            ],
            "daily": [
                "Limpia el polvo de la unidad con un paño seco",
                "Retira cualquier cinta, papel o cuerpo extraño del equipo",
                "Verifica que todas las piezas estén presentes y conectadas",
                "Verifica que los cables no estén retorcidos y retira del servicio si se ve cualquier daño",
                "Enciende y verifica que todos los indicadores funcionen",
            ],
            "weekly": [
                "Limpia todo el polvo y la suciedad de la máquina de rayos X y de la sala",
                "Si algún enchufe, cable o toma está dañado, consulta al técnico biomédico",
                "Verifica que todas las perillas, interruptores y ruedas funcionen correctamente",
                "Verifica que los delantales de plomo no tengan defectos",
                "Verifica que la mesa, el portacasetes y las rejillas se muevan suavemente",
                "Si la máquina no ha estado en uso, usa el delantal de plomo y verifica si la luz de exposición se enciende al operar el interruptor",
                "Verifica la bombilla del collimador, reemplázala por el tipo correcto si es necesario",
            ],
        },
    },
]

GUIDE_INDEX = {g["slug"]: g for g in GUIDES}

CATEGORY_ICONS = {
    "anaesthetic_machine": "⛽",
    "autoclave_sterilizer": "🧪",
    "ecg_machine": "💓",
    "electronic_diagnostic_equipment": "🔍",
    "electrosurgical_unit": "🔥",
    "endoscope": "🔭",
    "infant_incubator": "👶",
    "lamp": "💡",
    "nebulizer": "🌫️",
    "oxygen_concentrator": "🫧",
    "oxygen_cylinder_flowmeter": "💨",
    "pulse_oximeter": "🖐️",
    "scale": "⚖️",
    "sphygmomanometer": "🩸",
    "stethoscope": "🩺",
    "suction_machine": "🌀",
    "operating_table": "🛏️",
    "ultrasound_machine": "📡",
    "xray_machine": "🔬",
}


def category_title(slug: str, lang: str = "en"):
    guide = GUIDE_INDEX.get(slug)
    if not guide:
        return None
    content = guide.get(lang) or guide
    return content.get("title")


CATEGORY_FALLBACKS = {
    "ventilator": {"en": "Ventilator", "fr": "Ventilateur", "es": "Ventilador"},
    "infusion_pump": {"en": "Infusion Pump", "fr": "Pompe à perfusion", "es": "Bomba de infusión"},
    "defibrillator": {"en": "Defibrillator", "fr": "Défibrillateur", "es": "Desfibrilador"},
    "other": {"en": "Other", "fr": "Autre", "es": "Otro"},
}


def category_label(cat, lang: str = "en", default: str = "—"):
    if not cat:
        return default
    slug = cat.get("slug")
    title = category_title(slug, lang)
    if title:
        return title
    fallback = CATEGORY_FALLBACKS.get(slug, {})
    return fallback.get(lang) or cat.get("name") or default