//Maya ASCII 2027 scene
//Name: MainHero_Skirt.ma
//Last modified: Fri, Nov 20, 2026 05:41:31 PM
//Codeset: 1252
requires maya "2027";
currentUnit -l centimeter -a degree -t ntsc;
fileInfo "application" "maya";
fileInfo "product" "Maya 2027";
fileInfo "version" "2027";
fileInfo "cutIdentifier" "202607171511-52c21617ee";
fileInfo "osv" "Windows 11 Home v2009 (Build: 26200)";
fileInfo "UUID" "3ABB6F6A-4901-B9B6-B09B-F2994CADC278";
createNode transform -s -n "persp";
	rename -uid "51621BD9-4E21-F04F-8085-A88E7600384E";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 28 21 28 ;
	setAttr ".r" -type "double3" -27.938352729602379 44.999999999999972 -5.172681101354183e-14 ;
createNode camera -s -n "perspShape" -p "persp";
	rename -uid "3CE7466A-4356-F2DC-7DA4-DEAAE3A6C74D";
	setAttr -k off ".v" no;
	setAttr ".fl" 34.999999999999993;
	setAttr ".coi" 44.82186966202994;
	setAttr ".imn" -type "string" "persp";
	setAttr ".den" -type "string" "persp_depth";
	setAttr ".man" -type "string" "persp_mask";
	setAttr ".hc" -type "string" "viewSet -p %camera";
createNode transform -s -n "top";
	rename -uid "0858AEA3-46DE-BF8C-8FF8-87B9AFE3DA65";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 0 1000.1 0 ;
	setAttr ".r" -type "double3" -90 0 0 ;
createNode camera -s -n "topShape" -p "top";
	rename -uid "97B1BF85-42D9-9F90-96FC-3F8BA7BA4132";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 1000.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "top";
	setAttr ".den" -type "string" "top_depth";
	setAttr ".man" -type "string" "top_mask";
	setAttr ".hc" -type "string" "viewSet -t %camera";
	setAttr ".o" yes;
createNode transform -s -n "front";
	rename -uid "865F91F3-439F-B9B1-8461-25A9649353F2";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 0 0 1000.1 ;
createNode camera -s -n "frontShape" -p "front";
	rename -uid "EEA95135-4258-66C3-B942-859839738C7A";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 1000.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "front";
	setAttr ".den" -type "string" "front_depth";
	setAttr ".man" -type "string" "front_mask";
	setAttr ".hc" -type "string" "viewSet -f %camera";
	setAttr ".o" yes;
createNode transform -s -n "side";
	rename -uid "2CD2B3BF-446A-7061-26A5-1EABB72675C3";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 1000.1 0 0 ;
	setAttr ".r" -type "double3" 0 90 0 ;
createNode camera -s -n "sideShape" -p "side";
	rename -uid "5B67EB37-48C8-22A2-FEEB-DE82BE8657E4";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 1000.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "side";
	setAttr ".den" -type "string" "side_depth";
	setAttr ".man" -type "string" "side_mask";
	setAttr ".hc" -type "string" "viewSet -s %camera";
	setAttr ".o" yes;
createNode joint -n "root";
	rename -uid "E1FB2DF5-4FEB-CB23-FA2E-C5B5D52A1D91";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".jo" -type "double3" -90 0 0 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 2;
createNode joint -n "pelvis" -p "root";
	rename -uid "04056686-480E-0E1D-B5CB-DDAB7335F57A";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.4314998759166215e-17 -2.2808661460876465 95.896781921386719 ;
	setAttr ".r" -type "double3" -90 -86.366893050032431 90 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0 0.99799027986901867 -0.063367194090933054 0 0 -0.063367194090933054 -0.99799027986901856 0
		 -1 0 0 0 -3.4314998759166215e-17 95.896781921386719 2.2808661460876465 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "spine_01" -p "pelvis";
	rename -uid "8BBEF5BA-4A92-15C8-8DA0-008BEEA645CE";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.6770534515381001 7.1054273576010019e-15 -4.6633694517662434e-16 ;
	setAttr ".r" -type "double3" -4.8675251569720316e-17 2.1703504497372443e-16 -14.457321828304911 ;
	setAttr ".s" -type "double3" 0.99999999999999978 0.99999999999999989 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0 0.98220797016103356 0.18779644126591361 0 0 0.18779644126591366 -0.98220797016103356 0
		 -1 0 0 0 4.3202194641745812e-16 99.566445524580573 2.0478615863412895 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "spine_02" -p "spine_01";
	rename -uid "A8371707-4A55-11B9-13B8-55AB8A81AC9F";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 6.7950572967529155 1.7763568394002505e-14 1.8559423937125809e-16 ;
	setAttr ".r" -type "double3" -8.7467656525930775e-18 2.1960301960102488e-16 3.4644695084247532 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0 0.99176140629857157 0.12809884065314411 0 0 0.12809884065314417 -0.99176140629857157 0
		 -1 0 0 0 2.4642770704620003e-16 106.24060495915218 3.3239491648694486 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "spine_03" -p "spine_02";
	rename -uid "0E205E4E-4FD7-D3C6-7E1F-7CBA500B8F0B";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 7.2382278442382812 -1.9539925233402755e-14 1.2292061026364971e-16 ;
	setAttr ".r" -type "double3" 7.7116540289099159e-17 2.1691490646910566e-16 10.946079405533537 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0 0.99804167658749543 -0.062552472328609832 0 0 -0.062552472328609776 -0.99804167658749543 0
		 -1 0 0 0 1.2350709678255032e-16 113.41919998506341 4.2511577600996988 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "spine_04" -p "spine_03";
	rename -uid "F38A1D48-4EAC-673A-3838-4CAB83FA32AD";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 8.5238933563232422 -7.1054273576010019e-15 2.5229931328786502e-16 ;
	setAttr ".r" -type "double3" 0.00044952872062768446 -2.3921337171503338e-12 5.8669839318741532 ;
	setAttr ".s" -type "double3" 1 0.99999999999999989 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 5.2939559203393771e-23 0.98641974755132855 -0.16424396987644224 0
		 -7.8457562571503496e-06 -0.16424396987138709 -0.98641974752096839 0 -0.99999999996922206 1.2886181543573101e-06 7.7392089065275053e-06 0
		 -1.287922165053147e-16 121.92640080146128 3.7179671567962753 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "spine_05" -p "spine_04";
	rename -uid "C8734AB2-4B19-DA8F-9EF6-9EB582E1D962";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 19.439800262451158 -1.7817309228007616e-07 8.1130192624775943e-13 ;
	setAttr ".r" -type "double3" -0.0004494978431558535 5.3458782907563942e-06 0.68138935939447021 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -1.8369095114106268e-13 0.98439676970875745 -0.17596306370077883 0
		 1.5897534121574511e-11 -0.17596306370077877 -0.98439676970875722 0 -1 -2.9782035875482524e-12 -1.561715840808363e-11 0
		 5.8647193620207408e-13 141.10220369806046 0.52509736383965011 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "neck_01" -p "spine_05";
	rename -uid "22ADCBC7-4099-1E13-CD8B-FE93A6487F17";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 11.887765884399442 1.0658141036401503e-14 1.5994409772213136e-15 ;
	setAttr ".r" -type "double3" -5.3236884653331409e-16 4.0208541712268971e-15 -23.928404052334628 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -6.6158600092334618e-12 0.9711605157890677 0.23842661884175748 0
		 1.4456684607833927e-11 0.23842661884175759 -0.97116051578906759 0 -1 -2.9782035875482524e-12 -1.561715840808363e-11 0
		 -1.5988025270225873e-12 152.80448203371725 -1.5667103417368851 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "neck_02" -p "neck_01";
	rename -uid "3AAB785F-4D3C-88CA-4663-DB86DC9CC9A1";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 5.1102595329284384 -6.3948846218409017e-14 -4.1190754660973504e-14 ;
	setAttr ".r" -type "double3" -9.7964785669111379e-05 1.7913575251998921e-14 1.9135286365136508 ;
	setAttr ".s" -type "double3" 1 0.99999999999999989 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -6.1294451692525523e-12 0.97858030038111232 0.20586547963661239 0
		 1.7098227304699773e-06 0.20586547963631158 -0.9785803003796818 0 -0.99999999999853828 3.5198747834749016e-07 -1.6732001030229289e-06 0
		 -3.5366373453067859e-11 157.76736431753201 -0.34828843989683644 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "head" -p "neck_02";
	rename -uid "BFCC0929-4B6E-EF0F-2BBA-47A8FA211A91";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 4.9129710197448446 -4.9737991503207013e-14 2.0180004314720307e-14 ;
	setAttr ".r" -type "double3" 9.5867333842692594e-05 -2.0167398412977789e-05 11.88016967271599 ;
	setAttr ".s" -type "double3" 0.99999999999999989 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 2.0731684602442676e-14 0.99999999999999967 -2.7642915900707275e-08 0
		 -5.2736971644069353e-13 -2.764291584511913e-08 -1 0 -1 2.0731699954914845e-14 5.2736972046410003e-13 0
		 -6.5500340026078519e-11 162.57510097379762 0.66312269552376124 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "clavicle_l" -p "spine_05";
	rename -uid "67BEFB0F-4545-B0F3-EA12-4D93404F5F47";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 5.5162687301636311 1.3147660493850672 -1.4279042482376099 ;
	setAttr ".r" -type "double3" 163.26358510455574 80.83122589010857 153.12438365112951 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000002 0.99999999999999944 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.98722325285369927 -0.15258975017460921 -0.04589789937036267 0
		 -0.045885930500282501 0.0036018072449419511 -0.99894019258747135 0 0.15259334981277772 0.98828305415312057 -0.0034459348070640019 0
		 1.4279042482580846 146.30105055478367 -1.7398136340318517 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "upperarm_l" -p "clavicle_l";
	rename -uid "C708BA75-4C6C-D0B4-7C32-1286097F36E4";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 17.809522628784187 1.6431300764452317e-14 5.6843418860808015e-14 ;
	setAttr ".r" -type "double3" -4.3373452619178403 46.029604216550808 -4.3585186559704923 ;
	setAttr ".s" -type "double3" 1 0.99999999999999978 0.99999999999999967 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.57603356970603881 -0.81709064454000013 0.023413781773248588 0
		 -0.032592100671480363 -0.051578494511193465 -0.99813697150129621 0 0.81677602899787549 0.57419729841681155 -0.056341644857918607 0
		 19.00987910961798 143.58349994612851 -2.5572333114820021 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "lowerarm_l" -p "upperarm_l";
	rename -uid "1F9B3AB2-47B5-1BD7-0599-EBA3A7A55210";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 27.771139144897504 1.3322676295501878e-14 -1.1368683772161603e-13 ;
	setAttr ".r" -type "double3" -1.1529510720305249e-14 3.5781240166464568e-15 -38.978821942625935 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.46829763500528582 -0.60274413765566637 0.64606255855774819 0
		 0.33700777958812461 -0.55407307010227569 -0.76120220013116158 0 0.81677602899787549 0.57419729841681155 -0.056341644857918607 0
		 35.006987526056307 120.89196196261412 -1.9070059199488574 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "lowerarm_twist_02_l" -p "lowerarm_l";
	rename -uid "E08A9CA0-4CDC-5BA6-1DDE-CEB545F4290E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 9.0836915969848633 -7.1054273576010019e-14 9.9475983006414026e-14 ;
	setAttr ".r" -type "double3" 1.2856768460267047 -1.7275331230962776 1.9858280815512741 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.50409945495245201 -0.60398945624054479 0.61731716019149607 0
		 0.33849062611899527 -0.51942160302091644 -0.78461792889581128 0 0.79454882514934966 0.60448154236951845 -0.057395377761239416 0
		 39.260858818041761 115.41682010425956 3.96162711434875 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "lowerarm_twist_01_l" -p "lowerarm_l";
	rename -uid "6173084E-480E-C038-0FE7-13B6B461187B";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 18.167383193969734 -2.8421709430404007e-14 7.1054273576010019e-14 ;
	setAttr ".r" -type "double3" 1.2856768693497316 -1.7275255464774961 1.9858281662294717 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000002 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.50409934937944101 -0.60398953540120925 0.61731716895049749 0
		 0.3384906272290289 -0.51942160364797829 -0.7846179280018154 0 0.79454889165697262 0.60448146273446102 -0.057395295774846602 0
		 43.514730110027159 109.94167824590484 9.8302601486462819 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "hand_l" -p "lowerarm_l";
	rename -uid "774D05BE-4BCD-BE4B-C5F9-C98EDA56CF52";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 27.251073837280284 -2.1316282072803006e-14 9.9475983006414026e-14 ;
	setAttr ".r" -type "double3" -67.770758746900071 1.4734707800079263 1.8489162697849526 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000011 0.99999999999999956 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.45776606561811412 -0.63486683690404522 0.62241009677540249 0
		 -0.6455090443714524 -0.71872771411568381 -0.25835740089399245 0 0.61136593199422506 -0.28350409584606823 -0.73882144313449338 0
		 47.768600955409156 104.46653696237179 15.698892566810567 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_metacarpal_l" -p "hand_l";
	rename -uid "50C416CE-4E92-521E-5C07-388445757BB1";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.3758335113525533 -0.75357073545451669 -0.18286436796188354 ;
	setAttr ".r" -type "double3" -4.2725003027381687 -0.13075114456698561 -2.3183915821069538 ;
	setAttr ".s" -type "double3" 0.99999999999999978 0.99999999999999967 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.48489773769626732 -0.60591821332048423 0.63066417588408685 0
		 -0.67018644860059928 -0.72073617183479377 -0.17717080662751097 0 0.56189350244433178 -0.33675286097587692 -0.7555615147262349 0
		 49.688582660644784 102.91678718852391 18.129840122146437 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_01_l" -p "middle_metacarpal_l";
	rename -uid "0898D6D8-403F-0FB5-3F5C-A1B5562346DF";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 6.0982089042663432 5.6843418860808015e-14 1.4210854715202004e-14 ;
	setAttr ".r" -type "double3" 6.3611093629270351e-15 -3.1805546814635148e-15 31.57268201739824 ;
	setAttr ".s" -type "double3" 1.0000000000000009 1 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.062225503872753773 -0.89359104695641389 0.44454811603146327 0
		 -0.8248658548992216 -0.29680389388264872 -0.48114838667242188 0 0.561893502444332 -0.33675286097587709 -0.75556151472623523 0
		 52.645590362322736 99.221771344795741 21.975762015124548 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_02_l" -p "middle_01_l";
	rename -uid "B789626D-4CE7-3848-7020-E38C339FC0E4";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 5.1690001487731934 -1.4210854715202004e-14 4.2632564145606011e-14 ;
	setAttr ".r" -type "double3" 6.3611093629270335e-15 1.4312496066585827e-14 20.769210477739517 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.23431932551154863 -0.94077026842430223 0.24504235499333737 0
		 -0.79332852312434521 0.039354957418722358 -0.60752040436837751 0 0.561893502444332 -0.33675286097587709 -0.75556151472623523 0
		 52.967234001098525 94.602799090135633 24.273631293028 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_03_l" -p "middle_02_l";
	rename -uid "F4EB25C8-463F-D9E1-3EA0-BDA730D451F1";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 2.4739999771118164 4.2632564145606011e-14 0 ;
	setAttr ".r" -type "double3" 2.544443745170814e-14 5.5659706925611543e-15 9.9999999709533771 ;
	setAttr ".s" -type "double3" 1 0.99999999999999989 0.99999999999999967 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.36851954040065671 -0.91964393761217478 0.13582480022464374 0
		 -0.74058695657817952 0.20212010943431011 -0.6408419626620383 0 0.56189350244433178 -0.33675286097587698 -0.75556151472623501 0
		 52.387527995146066 92.275333467586435 24.879866073672915 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_metacarpal_l" -p "hand_l";
	rename -uid "AA09A4C3-4C81-5AB1-7A91-EC855B45D24E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.3143784999847554 -0.30591726303099165 2.3911108970642037 ;
	setAttr ".r" -type "double3" -27.769049129171513 -19.527703069996932 11.850627289629655 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 0.99999999999999944 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.50165929984922653 -0.81946977563034828 0.27714118009262256 0
		 -0.86150484141863282 -0.50229885137241914 0.074197520997708155 0 0.078405070544199928 -0.27598034484052558 -0.95796006919634324 0
		 50.945127063517511 101.90432945001062 16.074227195038095 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_01_l" -p "pinky_metacarpal_l";
	rename -uid "5200829B-4A82-EA71-D2EC-46B78D79507E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 4.9575676918029927 -0.14312039315700531 -0.19884027540683746 ;
	setAttr ".r" -type "double3" 10.491640062438089 0.60504264270137542 14.833680882858816 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.2635405017513856 -0.91778928814692995 0.29700038131184431 0
		 -0.93037057822145863 -0.32317414573818048 -0.17311573789308446 0 0.25486661436229252 -0.23069740806768885 -0.93905362721963437 0
		 53.539845826532741 97.968517782802252 17.628035221144721 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_02_l" -p "pinky_01_l";
	rename -uid "2598D9BD-4940-0674-6D05-F688AEEB5359";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.8159999847411825 1.8474111129762605e-13 6.3948846218409017e-14 ;
	setAttr ".r" -type "double3" -3.1805546814635168e-15 0 21.28699904924385 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.092201469831925953 -0.9724969364063768 0.21388921815053269 0
		 -0.96257046383334244 0.032068903802027982 -0.26912764176985227 0 0.25486661436229252 -0.23069740806768885 -0.93905362721963437 0
		 54.545516377194559 94.466233873237869 18.761388671698754 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_03_l" -p "pinky_02_l";
	rename -uid "1D392A30-424E-B41A-7A1B-6D9114BD6FCC";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 2.0399999618530416 7.1054273576010019e-15 1.7763568394002505e-14 ;
	setAttr ".r" -type "double3" 0 -3.1805546814635168e-15 4.9170000470223698 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.17436652109979212 -0.96616935149144467 0.19003447202589094 0
		 -0.9511252941663676 0.11530607160706441 -0.28647021598673916 0 0.25486661436229252 -0.23069740806768885 -0.93905362721963437 0
		 54.357425382254632 92.482340160066656 19.197722668566598 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_metacarpal_l" -p "hand_l";
	rename -uid "8BABCB75-4646-EB42-7505-88BD8DD45435";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.3743038177490234 -0.54251688718794355 1.0917565822601283 ;
	setAttr ".r" -type "double3" -13.299834889366425 -11.809318654920906 -1.5945633604277318 ;
	setAttr ".s" -type "double3" 0.99999999999999989 0.99999999999999989 0.99999999999999967 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.59060503118117402 -0.65963271076520424 0.46483371653961758 0
		 -0.73083333884862711 -0.68147046384688714 -0.038479055753444874 0 0.34215249227625494 -0.31699005314497924 -0.88456146097164412 0
		 50.330905076088669 102.40470783030432 17.132643411823313 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_01_l" -p "ring_metacarpal_l";
	rename -uid "407F76B5-4653-BF41-6B67-FCAE06E76E7E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 5.6455168724060023 -0.041624534875168706 -0.020689174532893873 ;
	setAttr ".r" -type "double3" 6.3958444445851228 -0.11693801365857265 29.414482479749061 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.15623819408419617 -0.90993079452509829 0.38420772491483429 0
		 -0.88283473502988641 -0.30308700145347278 -0.35880510054158071 0 0.44293617749515529 -0.28313286408480798 -0.85067227763758335 0
		 53.688517489721136 98.715664385711946 19.776772520660199 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_02_l" -p "ring_01_l";
	rename -uid "74AA1E84-4E03-592A-0BE9-42BE3B5E5362";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 4.9770002365112447 -7.1054273576010019e-14 -9.5923269327613525e-14 ;
	setAttr ".r" -type "double3" -3.1805546814635176e-15 7.9513867036587888e-15 18.963999541971795 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.13914028536722992 -0.95903783110600926 0.2467517365600666 0
		 -0.88569042201770853 0.0090675124822772735 -0.4641877384889419 0 0.4429361774951554 -0.28313286408480803 -0.85067227763758357 0
		 54.46611501863029 94.186938606151713 21.688974458430884 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_03_l" -p "ring_02_l";
	rename -uid "127A32B1-4CB7-097A-354D-13A4E982158D";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 2.265000104904189 3.5527136788005009e-14 1.5987211554602254e-13 ;
	setAttr ".r" -type "double3" 0 2.2263882770244614e-14 9.1679997480249913 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.27847973581337387 -0.94534178719106776 0.16964062641865238 0
		 -0.85220688767886321 0.16175502052651367 -0.49757284283527181 0 0.4429361774951554 -0.28313286408480803 -0.85067227763758357 0
		 54.150962257677158 92.014717818089466 22.247867167624573 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thumb_01_l" -p "hand_l";
	rename -uid "2459D9A1-4241-8534-D5CF-9C92A7C298B5";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 1.992446541786201 1.3566048145294474 -2.5815360546112114 ;
	setAttr ".r" -type "double3" 73.564463907750024 39.90417842702314 20.508675504416569 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000004 0.99999999999999867 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.23677732947120186 -0.46744570505554739 0.85172237793403616 0
		 0.35804510680805463 -0.85693276787306882 -0.37076937958279521 0 0.90318336883453154 0.21716524623089306 0.37026889970693044 0
		 46.226711496376346 102.95844529643908 18.495816711153008 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thumb_02_l" -p "thumb_01_l";
	rename -uid "E1EDD2A9-4EE9-5058-C2C1-C8B67C4C0171";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 4.3779997825622416 9.9475983006414026e-14 -7.1054273576010019e-14 ;
	setAttr ".r" -type "double3" 3.5306280002014567 -1.9322904957701326 23.246005781061328 ;
	setAttr ".s" -type "double3" 1 1.0000000000000004 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.045744985004836883 -0.75995290887963518 0.64836638764844179 0
		 0.47737462531297947 -0.58677024939719435 -0.65407502744688883 0 0.87750832671502266 0.27959300904660811 0.38962403139188362 0
		 45.190100399435728 100.91196810134613 22.22465709655155 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thumb_03_l" -p "thumb_02_l";
	rename -uid "9EB8734A-4DA2-9D71-28F5-82BE6A786C05";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.0859999656677246 4.2632564145606011e-14 7.1054273576010019e-14 ;
	setAttr ".r" -type "double3" -3.1805546814635176e-15 -3.1805546814635164e-15 9.9999999709533807 ;
	setAttr ".s" -type "double3" 1 0.99999999999999978 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.037845217613482196 -0.8502991008797891 0.5249373091587336 0
		 0.47806576540219692 -0.44589145353469928 -0.75672579949088947 0 0.87750832671502255 0.27959300904660805 0.38962403139188356 0
		 45.048931377281413 98.566753450634479 24.225515746574747 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_metacarpal_l" -p "hand_l";
	rename -uid "26B00FE3-474F-4ED8-974C-6DBD987F02A1";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.4445061683654821 -0.3846808075904562 -2.3793244361877459 ;
	setAttr ".r" -type "double3" 3.2877464546581483 7.3255016683865124 -0.60616237917610527 ;
	setAttr ".s" -type "double3" 1 0.99999999999999956 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.38282471691666847 -0.58595958989602792 0.71421046976822766 0
		 -0.60140250132809681 -0.74492304281921029 -0.28879870441758848 0 0.70125620675611955 -0.31896868072876305 -0.63757251603262366 0
		 48.139056031148343 103.23076320707465 19.700069031658664 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_01_l" -p "index_metacarpal_l";
	rename -uid "83EB876C-4581-FF38-B6C1-FD921AA83A05";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 5.8770980834960902 0.043181736022219752 0.24087569117545549 ;
	setAttr ".r" -type "double3" 1.2722218725854073e-14 1.2722218725854067e-14 23.372999646513961 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.11282515358796361 -0.8333991415651697 0.54103267512812159 0
		 -0.70392486616390482 -0.45133673853630707 -0.54843863033482487 0 0.70125620675611955 -0.31896868072876305 -0.63757251603262366 0
		 50.531900410692231 99.678022352664797 23.731507464854804 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_02_l" -p "index_01_l";
	rename -uid "D958BC96-43A1-1812-5136-74BE80133B8D";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 4.0799999237060547 0 -9.0594198809412774e-14 ;
	setAttr ".r" -type "double3" 3.1805546814635195e-15 9.5416640443905503e-15 14.892568419110976 ;
	setAttr ".s" -type "double3" 1.0000000000000002 0.99999999999999967 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.071878640933651761 -0.92140168606419925 0.38190626323167681 0
		 -0.70927652820571307 -0.22198629154117516 -0.66906568653925691 0 0.70125620675611944 -0.318968680728763 -0.63757251603262355 0
		 50.992227028723185 96.277753918662242 25.93892073810008 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_03_l" -p "index_02_l";
	rename -uid "BF63893B-47F7-7BB0-8B59-D2A5ADC46166";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 2.5950000286102437 7.1054273576010019e-14 -2.1316282072803006e-14 ;
	setAttr ".r" -type "double3" -3.1805546814635187e-15 1.7493050748049344e-14 12.516400997546974 ;
	setAttr ".s" -type "double3" 1.0000000000000002 0.99999999999999933 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.22388412434001692 -0.94761232662415895 0.22783058903152797 0
		 -0.67684239772233667 -0.017025250192035518 -0.73593104942064802 0 0.70125620675611944 -0.318968680728763 -0.63757251603262355 0
		 50.80570195344383 93.886716516964114 26.929967502112678 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "weapon_l" -p "hand_l";
	rename -uid "0A3E0598-4E30-B1A8-8D04-21A8CB58DB5B";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 1.1633778810501241 1.3170588016510436 0.51951599121093395 ;
	setAttr ".r" -type "double3" -11.617611580307605 -15.808370734790156 8.5170863439819282 ;
	setAttr ".s" -type "double3" 1.0000000000000002 0.99999999999999978 0.99999999999999956 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.5101570886898299 -0.78377147370740308 0.35417795225288096 0
		 -0.79058848355508882 -0.589491018503433 -0.16574133091613166 0 0.33868804899137267 -0.19545489532450003 -0.92037372266058592 0
		 47.768596880562413 102.63405535367295 15.698889263164309 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "upperarm_twist_01_l" -p "upperarm_l";
	rename -uid "01545CBE-4AA4-C937-D152-239A3F2A958C";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 9.2570457458496378 1.1546319456101628e-14 -9.9475983006414026e-14 ;
	setAttr ".r" -type "double3" 2.6828436514387616e-10 -2.1533312395632254 -0.32660888591551879 ;
	setAttr ".s" -type "double3" 1.0000000000000004 0.99999999999999978 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.60649254765415872 -0.79463176670251345 0.026965626030396716 0
		 -0.029307966917277297 -0.05623537513571026 -0.99798728732310094 0 0.7945488233677932 0.60448154473944693 -0.057395377464279168 0
		 24.342248215531768 136.0196544711159 -2.3404908625237053 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "upperarm_twist_02_l" -p "upperarm_l";
	rename -uid "FB8F535E-4808-DF94-BAF2-358C2852E834";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 18.514091491699276 8.8817841970012523e-15 -9.9475983006414026e-14 ;
	setAttr ".r" -type "double3" -2.7829853462805776e-15 4.4478069373591348e-15 3.975693351829394e-16 ;
	setAttr ".s" -type "double3" 1.0000000000000004 0.99999999999999989 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.57603356970603903 -0.81709064454000047 0.023413781773248599 0
		 -0.032592100671480356 -0.051578494511193458 -0.9981369715012961 0 0.81677602899787571 0.57419729841681166 -0.056341644857918621 0
		 29.674617321445631 128.45580899610337 -2.1237484135654001 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "clavicle_r" -p "spine_05";
	rename -uid "87E969E6-45D3-9DE0-98D7-279443506364";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 5.5162200927734375 1.314811229705807 1.4278726577758791 ;
	setAttr ".r" -type "double3" 163.26358510455586 80.831225890108584 -26.875616348870519 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000004 0.99999999999999967 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.98722325285135692 0.15258975018048915 0.045897899401197824 0
		 -0.045885930531461866 -0.003601807245217459 0.99894019258603828 0 0.15259334981855652 -0.98828305415221218 0.0034459348118279862 0
		 -1.4278726577554037 146.30099472621771 -1.739849551054053 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "upperarm_r" -p "clavicle_r";
	rename -uid "0058AC87-4DAE-67EF-A60F-13B3E8C44FB9";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -17.809625625610355 2.8716144648832653e-06 0.00043809693306684494 ;
	setAttr ".r" -type "double3" -4.337345261917843 46.029604216550808 -4.3585186559704807 ;
	setAttr ".s" -type "double3" 1 0.99999999999999978 0.99999999999999944 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.57603356970190345 0.8170906445434315 -0.02341378175525494 0
		 -0.032592100702963554 0.051578494510997164 0.99813697150027847 0 0.81677602899953572 -0.574197298411947 0.056341644883428681 0
		 -19.009882481023482 143.58299542707977 -2.5572695781667329 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "lowerarm_r" -p "upperarm_r";
	rename -uid "8FBCC084-4895-1DA5-2DB4-48BC4382CCC3";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -27.770694732666016 -3.4638958368304884e-14 5.6843418860808015e-14 ;
	setAttr ".r" -type "double3" -1.1529510720305249e-14 1.5505204072134644e-14 -38.978821942625942 ;
	setAttr ".s" -type "double3" 1 1 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.46829763502187488 0.60274413765845714 -0.64606255854312011 0
		 0.33700777956104905 0.55407307010428153 0.76120220014168893 0 0.81677602899953594 -0.57419729841194711 0.056341644883428695 0
		 -35.006734900982885 120.89182056854678 -1.9070525925043142 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "lowerarm_twist_02_r" -p "lowerarm_r";
	rename -uid "17C218AF-40AB-865E-A2AA-32A968CB5CFE";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -9.0836620330810547 -1.4210854715202004e-14 -1.4210854715202004e-14 ;
	setAttr ".r" -type "double3" 1.285676846026711 -1.7275331230962687 1.9858280815512903 ;
	setAttr ".s" -type "double3" 1 1 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.50409945496813557 0.60398945624354872 -0.61731716017574922 0
		 0.33849062609139469 0.51942160302293094 0.78461792890638504 0 0.79454882515115777 -0.60448154236478657 0.057395377786055017 0
		 -39.260592348412757 115.41669652963647 3.9615613415290207 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "lowerarm_twist_01_r" -p "lowerarm_r";
	rename -uid "1FD089A5-4F57-61BE-1C23-C3A879214D4C";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -18.167304992675781 -7.1054273576010019e-15 -1.4210854715202004e-14 ;
	setAttr ".r" -type "double3" 1.2856768693497385 -1.7275255464774895 1.9858281662294912 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.50409934939512469 0.60398953540421341 -0.61731716893475086 0
		 0.33849062720142825 0.51942160364999246 0.78461792801238917 0 0.79454889165878051 -0.60448146272972902 0.057395295799662197 0
		 -43.51444086377407 109.94158398715824 9.8301629528969965 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "hand_r" -p "lowerarm_r";
	rename -uid "06B77F40-4C21-9A1C-B317-7993B98C14D1";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -27.251010894775412 -7.1054273576010019e-15 0 ;
	setAttr ".r" -type "double3" -67.770758746900086 1.4734707800079416 1.8489162697849597 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000007 0.99999999999999956 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.45776606563377292 0.63486683690677337 -0.62241009676110326 0
		 -0.64550904438380341 0.71872771411183844 0.2583574008738318 0 0.61136593196945999 0.28350409584970843 0.73882144315358966 0
		 -47.768318854961556 104.46643350645415 15.698805229060721 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_metacarpal_r" -p "hand_r";
	rename -uid "C5404CCC-4367-3011-D34B-5293ABAC7D9D";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.3758001327514471 0.75400394201277265 0.18280552327632194 ;
	setAttr ".r" -type "double3" -4.2725003027381421 -0.1307511445669825 -2.3183915821069596 ;
	setAttr ".s" -type "double3" 0.99999999999999967 0.99999999999999933 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.48489773771235634 0.60591821332337392 -0.6306641758689403 0
		 -0.67018644861042598 0.72073617183080163 0.17717080660657977 0 0.56189350241872704 0.33675286097922214 0.75556151474378597 0
		 -49.688600895060446 102.91699959841172 18.129800455563196 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_01_r" -p "middle_metacarpal_r";
	rename -uid "B61EFD77-4043-29F9-4F8C-8BAAAB339084";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -6.0983657836914205 -0.0001238507247620646 1.430381864508945e-06 ;
	setAttr ".r" -type "double3" 6.3611093629270351e-15 3.180554681463516e-15 31.572682017398236 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.062225503881316258 0.89359104695678526 -0.44454811602951783 0
		 -0.82486585491601749 0.29680389387773476 0.48114838664665849 0 0.56189350241872726 0.3367528609792223 0.7555615147437863 0
		 -52.645600860515195 99.221799916552953 21.975800424690974 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_02_r" -p "middle_01_r";
	rename -uid "5497A187-41B3-18AE-8799-CC95F46AA277";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -5.1689915657043315 -7.7438591688405722e-05 -3.7045669152746541e-05 ;
	setAttr ".r" -type "double3" 3.180554681463516e-15 1.4312496066585818e-14 20.769210477739527 ;
	setAttr ".s" -type "double3" 1.0000000000000007 1.0000000000000002 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.23431932550949874 0.94077026842290723 -0.24504235500065422 0
		 -0.79332852314308611 -0.039354957423448855 0.60752040434359866 0 0.56189350241872738 0.33675286097922236 0.75556151474378652 0
		 -52.967200904520077 94.602799872333804 24.273600637261946 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_03_r" -p "middle_02_r";
	rename -uid "DC20D660-48A1-E8A9-2B53-7398BCD6D8EA";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -2.4740469455719136 4.577730578603223e-05 3.4385015172944122e-05 ;
	setAttr ".r" -type "double3" 3.1805546814635176e-15 1.033680271475643e-14 9.9999999709533824 ;
	setAttr ".s" -type "double3" 0.99999999999999989 0.99999999999999989 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.36851954040189233 0.91964393760998009 -0.13582480023615218 0
		 -0.7405869565969917 -0.20212010943872263 0.64084196263890647 0 0.56189350241872749 0.33675286097922241 0.75556151474378674 0
		 -52.38750088868062 92.27529984094555 24.879900717828534 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_metacarpal_r" -p "hand_r";
	rename -uid "C60C3488-4836-8B42-80FB-12A69365F0B0";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.3146772384643484 0.30593535304068098 -2.3912868499755913 ;
	setAttr ".r" -type "double3" -27.769049129171496 -19.527703069996946 11.850627289629651 ;
	setAttr ".s" -type "double3" 0.99999999999999989 0.99999999999999978 0.99999999999999944 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.50165929985300162 0.81946977563333701 -0.27714118007695171 0
		 -0.86150484141930728 0.50229885136728791 -0.074197521024615631 0 0.078405070512635011 0.27598034484099043 0.95796006919879284 0
		 -50.945100964285352 101.90399945334072 16.074200470938983 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_01_r" -p "pinky_metacarpal_r";
	rename -uid "1DC3915A-4E36-1910-A5C7-78AB52563EFD";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -4.9573006629943919 0.14326146245002747 0.19892024993895774 ;
	setAttr ".r" -type "double3" 10.491640062438105 0.60504264270136832 14.833680882858816 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000002 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.2635405017551955 0.91778928814850058 -0.29700038130361062 0
		 -0.93037057822879088 0.32317414573263875 0.1731157378640259 0 0.25486661433158819 0.23069740806920463 0.93905362722759578 0
		 -53.539801031310596 97.968499538497568 17.628000637701916 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_02_r" -p "pinky_01_r";
	rename -uid "4CE20B37-4137-CB38-DEB2-D1BB1BC00932";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.8160362243652344 3.0366025399075625e-05 3.2629206547341028e-05 ;
	setAttr ".r" -type "double3" 6.3611093629270367e-15 1.4312496066585827e-14 21.28699904924385 ;
	setAttr ".s" -type "double3" 1 0.99999999999999989 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.092201469831037886 0.97249693640582791 -0.21388921815341003 0
		 -0.96257046384155742 -0.032068903807761784 0.26912764173978709 0 0.25486661433158825 0.23069740806920469 0.939053627227596 0
		 -54.545501068157023 94.466199709576202 18.761400748818435 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_03_r" -p "pinky_02_r";
	rename -uid "33D9948E-4982-2308-E9CA-B681CF62E12E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -2.0399997234344625 -1.7523876529423887e-05 -3.1002964529847077e-05 ;
	setAttr ".r" -type "double3" 1.7075473052254064e-06 9.5416640325420615e-15 4.9170000470223654 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000002 1.0000000000000007 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.17436652109961143 0.96616935149040684 -0.19003447203133475 0
		 -0.95112528657901119 -0.1153060647374114 0.28647024394301029 0 0.25486664267733117 0.2306974115055935 0.93905361869011839 0
		 -54.357401128856097 92.482299637935398 19.197700865091143 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_metacarpal_r" -p "hand_r";
	rename -uid "5F13B0EA-465C-7FF7-9AEC-83B6CB80EC5F";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.3742079734802175 0.54299175739286909 -1.0917816162109411 ;
	setAttr ".r" -type "double3" -13.299834889366398 -11.809318654920911 -1.5945633604277225 ;
	setAttr ".s" -type "double3" 0.99999999999999978 0.99999999999999978 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.59060503119176344 0.65963271076872343 -0.46483371652116912 0
		 -0.73083333885388824 0.68147046384253407 0.038479055730619577 0 0.3421524922467386 0.31699005314701523 0.8845614609823319 0
		 -50.33090093933658 102.40499942786849 17.132600610165039 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_01_r" -p "ring_metacarpal_r";
	rename -uid "2790B1A2-455B-B93E-5AD8-63A09ACAC955";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -5.6457118988037216 0.041443493217229843 0.02067497372626903 ;
	setAttr ".r" -type "double3" 6.3958444445851219 -0.1169380136585665 29.414482479749058 ;
	setAttr ".s" -type "double3" 1 0.99999999999999989 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.15623819409077647 0.90993079452602965 -0.38420772490995236 0
		 -0.88283473504289867 0.30308700144821343 0.35880510051400683 0 0.44293617746689906 0.28313286408744437 0.85067227765141862 0
		 -53.688501084163399 98.715699461407652 19.776800845944017 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_02_r" -p "ring_01_r";
	rename -uid "EC6BC5C8-4A26-B18A-8841-66BEC5BE7EAD";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -4.9770674705505371 -2.0846833649557084e-05 -2.3612021323060617e-05 ;
	setAttr ".r" -type "double3" 9.5416640443905487e-15 -3.1805546814635152e-15 18.963999541971834 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000002 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.13914028536523607 0.95903783110518104 -0.24675173656441018 0
		 -0.88569042203215298 -0.0090675124875544411 0.46418773846127842 0 0.44293617746689917 0.28313286408744442 0.85067227765141884 0
		 -54.466101171939769 94.186899499776416 21.68900104948537 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_03_r" -p "ring_02_r";
	rename -uid "B831BC2D-43F3-028F-ACF2-86B8FD72BCD6";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -2.2649745941161967 5.0017570174532011e-05 -1.1221488421142567e-05 ;
	setAttr ".r" -type "double3" 6.3611093629270367e-15 -6.3611093629270335e-15 9.1679997480249735 ;
	setAttr ".s" -type "double3" 1 0.99999999999999956 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.27847973581370661 0.9453417871894092 -0.16964062642734823 0
		 -0.85220688769344044 -0.16175502053159105 0.49757284280865344 0 0.44293617746689917 0.28313286408744442 0.85067227765141884 0
		 -54.151001231055453 92.014699546819784 22.24790113559148 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thumb_01_r" -p "hand_r";
	rename -uid "35E1D956-4472-89CC-CC8C-44BA36F6CD22";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -1.9928325414657593 -1.3566571474075317 2.5813255310058487 ;
	setAttr ".r" -type "double3" 73.564463907750024 39.90417842702314 20.508675504416569 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 0.99999999999999867 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.23677732944738347 0.46744570505413874 -0.85172237794143069 0
		 0.35804510679136936 0.85693276787520078 0.37076937959398015 0 0.90318336884739048 -0.21716524622551259 -0.37026889967872045 0
		 -46.226701019175849 102.95799948474078 18.495800563608931 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thumb_02_r" -p "thumb_01_r";
	rename -uid "31B1894A-492E-F493-0A98-1DB8B1E37F25";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -4.3778247833251811 0.00042712956201285124 -0.00013574546028394252 ;
	setAttr ".r" -type "double3" 3.5306280002014754 -1.9322904957701323 23.246005781061324 ;
	setAttr ".s" -type "double3" 0.99999999999999989 1 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.0457449849891126 0.75995290887936373 -0.64836638764986898 0
		 0.47737462528905472 0.5867702494000363 0.6540750274617998 0 0.8775083267288577 -0.27959300904138068 -0.38962403136447582 0
		 -45.190101029584021 100.91199959280999 22.224700527158511 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thumb_03_r" -p "thumb_02_r";
	rename -uid "2F998A23-4F6E-8F62-0D10-149D2789645E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.0859522819519114 -1.4851160820228415e-05 4.5825581779013191e-05 ;
	setAttr ".r" -type "double3" 1.2722218725854065e-14 1.5902773407317588e-15 9.9999999709533913 ;
	setAttr ".s" -type "double3" 0.99999999999999989 1.0000000000000002 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.037845217624813174 0.85029910088001526 -0.52493730915754966 0
		 0.47806576537590534 0.44589145353754533 0.75672579950582219 0 0.87750832672885792 -0.27959300904138074 -0.38962403136447593 0
		 -45.048901066006756 98.566799652746084 24.225500692146209 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_metacarpal_r" -p "hand_r";
	rename -uid "6A11343B-48B5-D249-3E15-E484B12A5A19";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.4445140361785747 0.38516682386398315 2.3793087005615163 ;
	setAttr ".r" -type "double3" 3.2877464546581714 7.3255016683865106 -0.60616237917610172 ;
	setAttr ".s" -type "double3" 0.99999999999999978 0.99999999999999967 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.38282471693548581 0.58595958989830976 -0.71421046975626912 0
		 -0.60140250134155437 0.74492304281562782 0.28879870439880584 0 0.70125620673430589 0.31896868073293855 0.63757251605452758 0
		 -48.139100880562282 103.230999608392 19.700100530986685 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_01_r" -p "index_metacarpal_r";
	rename -uid "9DBB064B-455F-F4CA-79A2-1C8311AEB15F";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -5.8772053718566966 -0.043412361294045354 -0.24095164239406408 ;
	setAttr ".r" -type "double3" 9.541664044390555e-15 -3.5311250384401278e-31 23.372999646513961 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.11282515359989806 0.83339914156584305 -0.54103267512459574 0
		 -0.70392486618372341 0.45133673853211353 0.54843863031283946 0 0.70125620673430589 0.31896868073293855 0.63757251605452758 0
		 -50.531900895495319 99.677999863184866 23.731500561889256 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_02_r" -p "index_01_r";
	rename -uid "FA8A9994-457D-035B-D215-72A4E38D898E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -4.079932689666748 5.0402059201815064e-06 3.2106661814523818e-05 ;
	setAttr ".r" -type "double3" 9.5416640443905582e-15 -1.5902773407317598e-15 14.892568419110976 ;
	setAttr ".s" -type "double3" 0.99999999999999956 0.99999999999999956 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.071878640927211662 0.9214016860637716 -0.38190626323391952 0
		 -0.70927652822793308 0.2219862915369494 0.66906568651710374 0 0.70125620673430589 0.31896868073293855 0.63757251605452758 0
		 -50.992200960814621 96.277799977819839 25.938900693876729 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_03_r" -p "index_02_r";
	rename -uid "5734A99F-4783-A1A6-5173-B2B8A8E05C82";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -2.5950763225555562 3.9602185992748673e-05 -3.5606819821509816e-06 ;
	setAttr ".r" -type "double3" 3.1805546814635168e-15 -4.4139062980501597e-32 12.516400997546972 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.22388412433854538 0.94761232662282568 -0.22783058903851844 0
		 -0.67684239774542487 0.017025250188002911 0.73593104939950804 0 0.70125620673430589 0.31896868073293855 0.63757251605452758 0
		 -50.80570098749827 93.886699934149348 26.930000821301533 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "weapon_r" -p "hand_r";
	rename -uid "181F31E4-48AD-061E-760B-1CA9D595B3BE";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -1.1633833646774221 -1.3170545101165771 -0.51951736211777799 ;
	setAttr ".r" -type "double3" -11.617611866448334 -15.808370499724777 8.5170885216315799 ;
	setAttr ".s" -type "double3" 1 0.99999999999999978 0.99999999999999967 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.51015706085696022 0.78377149596726137 -0.35417794308374112 0
		 -0.79058850044401541 0.58949099082372403 0.16574134880393657 0 0.33868805149203512 0.1954548895446358 0.92037372296780728 0
		 -47.768320898672442 102.63395111216924 15.698805434373773 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "upperarm_twist_01_r" -p "upperarm_r";
	rename -uid "35AC778A-4592-3081-1FF0-9B88CE576CFA";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -9.2568979263305522 1.0202637897194222e-05 -0.00010078256310919187 ;
	setAttr ".r" -type "double3" 2.6828754950018744e-10 -2.153331239563208 -0.32660888591551801 ;
	setAttr ".s" -type "double3" 1.0000000000000002 0.99999999999999978 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.60649254765026761 0.79463176670612623 -0.026965626011451752 0
		 -0.029307966948783556 0.056235375135533512 0.99798728732218578 0 0.79454882336960109 -0.60448154473471449 0.057395377489094922 0
		 -24.342249087200909 136.01932912929374 -2.3405260850142464 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "upperarm_twist_02_r" -p "upperarm_r";
	rename -uid "0DAAC6CE-4D61-2C2F-1970-0C9ECA01D5F9";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -18.513795852661133 2.0405275791723909e-05 -0.00020156512620417288 ;
	setAttr ".r" -type "double3" 1.987846675914698e-15 1.0597707590970231e-14 -1.1927080055488186e-15 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.57603356970190356 0.81709064454343172 -0.023413781755254943 0
		 -0.032592100702963554 0.051578494510997164 0.99813697150027847 0 0.81677602899953594 -0.57419729841194711 0.056341644883428695 0
		 -29.674615693378339 128.45566283150771 -2.1237825918617612 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thigh_r" -p "pelvis";
	rename -uid "E0019149-46BA-68FD-CDD0-E9BB5D16482E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -2.3657262325286723 -0.11948779225349782 9.9690914154052734 ;
	setAttr ".r" -type "double3" 8.4085386612241084 -3.1255399000842652 176.43986665923373 ;
	setAttr ".s" -type "double3" 1 0.99999999999999989 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.054523910657437981 -0.99851165534365671 0.0012717348352381946 0
		 -0.14601293308005975 0.0092329884397982023 0.98923959448549603 0 -0.98777900693423204 0.053751521535134156 -0.14629903414814571 0
		 -9.9690914154052734 93.543381742615168 2.550023234662302 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "calf_r" -p "thigh_r";
	rename -uid "6EFB2620-405B-B189-E3C7-EC9FDA3A59F3";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 43.341262817382777 -2.5757174171303632e-14 1.0658141036401503e-14 ;
	setAttr ".r" -type "double3" -6.3611093629270351e-15 -4.6714396883995417e-15 -5.0048445558743904 ;
	setAttr ".s" -type "double3" 0.99999999999999967 0.99999999999999989 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.041577864212587176 -0.9955101408023912 -0.085034350512737847 0
		 -0.15021289780688588 -0.07791234492852539 0.98557889173835111 0 -0.98777900693423204 0.053751521535134156 -0.14629903414814571 0
		 -12.332226557040798 50.266625662145813 2.6051418283903547 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "foot_r" -p "calf_r";
	rename -uid "9CFC202D-4E26-D2DD-9DAA-9C98EA3287C1";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 42.217948913574233 1.1102230246251565e-16 1.0658141036401503e-14 ;
	setAttr ".r" -type "double3" -0.0046626083855055749 3.0812019613373725 2.6641047060062926 ;
	setAttr ".s" -type "double3" 0.99999999999999989 1.0000000000000002 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.0046495256007424712 -0.99950197930304507 -0.031211781124816901 0
		 -0.14803750047914047 -0.031556184277057628 0.98847817663606585 0 -0.98897081876240256 2.4559475175288392e-05 -0.14811049602663431 0
		 -14.087558704303341 8.2382293948053729 -0.98483403745537856 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ball_r" -p "foot_r";
	rename -uid "49FB8D1B-4B1E-46BF-5CD4-099BDB5CF115";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 7.0094366073608354 15.237594604492184 -0.53894561529159546 ;
	setAttr ".r" -type "double3" 6.9773418324605905e-14 -6.5201370970002121e-14 -90.000000000000014 ;
	setAttr ".s" -type "double3" 0.99999999999999967 1 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.14803750047914041 0.031556184277057836 -0.98847817663606552 0
		 0.0046495256007425042 -0.99950197930304507 -0.031211781124817119 0 -0.98897081876240234 2.4559475175288385e-05 -0.14811049602663429 0
		 -15.777702081490759 0.75143005244908334 13.938242194727604 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "calf_twist_02_r" -p "calf_r";
	rename -uid "2560E8B0-4226-8503-83B0-948AD31A328B";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 14.072649955749519 6.8833827526759706e-15 0.037728950381282544 ;
	setAttr ".r" -type "double3" -0.0046559128746518717 0.25816272471228668 2.6643342814062057 ;
	setAttr ".s" -type "double3" 0.99999999999999989 0.99999999999999967 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.044064310719183021 -0.99828778764580239 -0.038468552846355794 0
		 -0.14803750057573373 -0.031556185440510864 0.98847817658445691 0 -0.98799961282590232 0.049251397926289076 -0.14639352737800071 0
		 -12.954605151152517 36.259187911723764 1.4029634704098872 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "calf_twist_01_r" -p "calf_r";
	rename -uid "A00D6B1E-4267-F376-0444-33B46EA0E48F";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 28.145299911499034 8.4376949871511897e-15 0.075457900762563312 ;
	setAttr ".r" -type "double3" -0.0046559128746518717 0.25816272471228668 2.6643342814062057 ;
	setAttr ".s" -type "double3" 0.99999999999999989 0.99999999999999967 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.044064310719183021 -0.99828778764580239 -0.038468552846355794 0
		 -0.14803750057573373 -0.031556185440510864 0.98847817658445691 0 -0.98799961282590232 0.049251397926289076 -0.14639352737800071 0
		 -13.576983745264235 22.251750161301715 0.20078511242941532 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thigh_twist_01_r" -p "thigh_r";
	rename -uid "94E79264-4DB5-6F82-F9D1-21A0F699C9B8";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 14.447087287902804 -3.5527136788005009e-15 -3.5527136788005009e-15 ;
	setAttr ".r" -type "double3" -2.065027893746282e-10 0.25820470285918773 -1.3073006136480809 ;
	setAttr ".s" -type "double3" 0.99999999999999956 1 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.046726521766803475 -0.99869449405102062 -0.02063830699820695 0
		 -0.14721887520437615 -0.013550178981221524 0.98901111997445978 0 -0.98799961282742133 0.049251397967495933 -0.14639352735388469 0
		 -10.75680311195109 79.117796699877033 2.568396098834052 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thigh_twist_02_r" -p "thigh_r";
	rename -uid "18E5C04C-403F-E0F5-7FD8-01BE66A9C1E4";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 28.894174575805629 -1.2434497875801753e-14 -3.3750779948604759e-14 ;
	setAttr ".r" -type "double3" -2.065027893746282e-10 0.25820470285918773 -1.3073006136480809 ;
	setAttr ".s" -type "double3" 0.99999999999999956 1 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.046726521766803475 -0.99869449405102062 -0.02063830699820695 0
		 -0.14721887520437615 -0.013550178981221524 0.98901111997445978 0 -0.98799961282742133 0.049251397967495933 -0.14639352735388469 0
		 -11.544514808496881 64.692211657138884 2.5867689630058006 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thigh_l" -p "pelvis";
	rename -uid "ABF127DA-4C3B-83BA-0248-DE862D31578E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -2.3657112121582031 -0.11004376411438344 -9.969202995300293 ;
	setAttr ".r" -type "double3" 8.4085386612241031 -3.1255399000842647 -3.5601333407662921 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.05452391065743796 0.99851165534365638 -0.0012717348352376742 0
		 -0.14601293308005966 -0.0092329884397976889 -0.98923959448549603 0 -0.98777900693423215 -0.053751521535134204 0.1462990341481456 0
		 9.969202995300293 93.542798291234817 2.5405972345779255 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "calf_l" -p "thigh_l";
	rename -uid "8159BDC0-4E3E-3A08-9E7A-7B8FEAD47FD8";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -43.341308593749993 6.2172489379008766e-15 5.3290705182007514e-15 ;
	setAttr ".r" -type "double3" -3.1805546814635187e-15 0 -5.0048445558743548 ;
	setAttr ".s" -type "double3" 0.99999999999999967 0.99999999999999967 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.041577864212587252 0.99551014080239086 0.085034350512737736 0
		 -0.15021289780688574 0.077912344928525237 -0.98557889173835078 0 -0.98777900693423204 -0.053751521535134197 0.14629903414814557 0
		 12.33234063284236 50.265996502529269 2.5957158865213779 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "foot_l" -p "calf_l";
	rename -uid "06569D4E-4180-FE4F-3428-D38026C790C2";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -42.217914581298842 -3.5527136788005009e-15 5.3290705182007514e-15 ;
	setAttr ".r" -type "double3" -0.0046626083855039946 3.0812019613373756 2.6641047060062952 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000011 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.0046495256007424504 0.9995019793030453 0.031211781124816786 0
		 -0.14803750047914047 0.031556184277057475 -0.9884781766360663 0 -0.98897081876240278 -2.455947517530227e-05 0.14811049602663423 0
		 14.087671352642205 8.2376344133171457 -0.99425705990160473 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ball_l" -p "foot_l";
	rename -uid "D1AE89E4-41EC-08A6-ED81-9EAE7C45951C";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -7.0094366073608327 -15.237588882446284 0.53888744115829468 ;
	setAttr ".r" -type "double3" 9.0447023754118737e-15 -6.3611093629270367e-15 -90.000000000000014 ;
	setAttr ".s" -type "double3" 0.99999999999999956 1.0000000000000002 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.14803750047914041 -0.031556184277057683 0.98847817663606585 0
		 0.0046495256007424842 0.99950197930304552 0.031211781124817012 0 -0.98897081876240256 -2.4559475175302263e-05 0.1481104960266342 0
		 15.777871415272493 0.75083525295552001 13.928804899964147 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "calf_twist_02_l" -p "calf_l";
	rename -uid "DC7AFFE9-40C4-D42B-6D8F-FBBA73804215";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -14.072638511657715 1.7763568394002505e-15 1.9539925233402755e-14 ;
	setAttr ".r" -type "double3" -0.0046559128746502809 0.2581627247122899 2.6643342814062074 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000004 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.04406431071918307 0.99828778764580262 0.03846855284635569 0
		 -0.14803750057573373 0.031556185440510726 -0.98847817658445736 0 -0.98799961282590276 -0.049251397926289082 0.14639352737800065 0
		 12.917450885992871 36.256542156327747 1.3990582106820248 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "calf_twist_01_l" -p "calf_l";
	rename -uid "9F783A2C-4EEB-FA92-025E-D5973763413A";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -28.145277023315437 5.0670109880135428e-06 -0.075448110699655402 ;
	setAttr ".r" -type "double3" -0.0046559128746502809 0.2581627247122899 2.6643342814062074 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000004 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.04406431071918307 0.99828778764580262 0.03846855284635569 0
		 -0.14803750057573373 0.031556185440510726 -0.98847817658445736 0 -0.98799961282590276 -0.049251397926289082 0.14639352737800065 0
		 13.577086437874987 22.251143655655984 0.19135755517993358 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thigh_twist_01_l" -p "thigh_l";
	rename -uid "63C0BBD9-4C2A-2F97-16E8-6E8EF51A44EF";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -14.447102546691895 8.8817841970012523e-16 3.5527136788005009e-15 ;
	setAttr ".r" -type "double3" -2.0649642897718216e-10 0.25820470285919295 -1.3073006136480436 ;
	setAttr ".s" -type "double3" 0.99999999999999978 1 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.046726521766803475 0.99869449405102062 0.020638306998206814 0
		 -0.14721887520437604 0.013550178981221378 -0.98901111997445978 0 -0.98799961282742133 -0.049251397967495884 0.14639352735388458 0
		 10.756915523814962 79.117198012417944 2.5589701181548041 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thigh_twist_02_l" -p "thigh_l";
	rename -uid "818E24E9-4EE3-F0AD-9DAD-0187121D5C05";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -28.894205093383796 -2.2688980125806779e-06 -8.0748641266836785e-06 ;
	setAttr ".r" -type "double3" -2.0649642897718216e-10 0.25820470285919295 -1.3073006136480436 ;
	setAttr ".s" -type "double3" 0.99999999999999978 1 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.046726521766803475 0.99869449405102062 0.020638306998206814 0
		 -0.14721887520437604 0.013550178981221378 -0.98901111997445978 0 -0.98799961282742133 -0.049251397967495884 0.14639352735388458 0
		 11.544636359799362 64.691598188585999 2.5773440648706107 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_hand_root" -p "root";
	rename -uid "9F4B705B-4C3C-09FB-B299-D9BADBBD8BD9";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_hand_gun" -p "ik_hand_root";
	rename -uid "10CCB98E-4E10-AF73-95FF-448C8D2898C0";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -47.768318176269531 -15.69880485534668 104.4664306640625 ;
	setAttr ".r" -type "double3" 68.473107478131155 -39.410111911239163 53.666512015145315 ;
	setAttr ".s" -type "double3" 0.99999999999999978 0.99999999999999978 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.45776599577967658 0.63486688008580827 -0.62241010409371778 0
		 -0.64550907761389853 0.71872766733298943 0.25835744798269883 0 0.61136594918746878 0.28350411774821049 0.7388214205028939 0
		 -47.768318176269531 104.4664306640625 15.69880485534668 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_hand_r" -p "ik_hand_gun";
	rename -uid "CAD41385-40AE-C1C5-9031-079E586BAE91";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -7.1054273576010019e-15 0 7.1054273576010019e-15 ;
	setAttr ".r" -type "double3" 3.3395824155366921e-14 -2.2263882770244611e-14 0 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.45776599577967669 0.63486688008580838 -0.62241010409371789 0
		 -0.64550907761389864 0.71872766733298954 0.25835744798269888 0 0.61136594918746878 0.28350411774821049 0.7388214205028939 0
		 -47.768318176269531 104.4664306640625 15.698804855346689 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_hand_l" -p "ik_hand_gun";
	rename -uid "E288A28D-4213-90CF-57FF-1A86D88D9313";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 43.73357009887696 -61.669849395751982 58.408111572265597 ;
	setAttr ".r" -type "double3" -107.73758596138391 -34.036790747396616 -134.50699481505316 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.4577661185092996 -0.63486684526340853 0.62241004934867228 0
		 -0.64550905383748758 -0.71872771643705491 -0.25835737078513543 0 0.61136588239675338 -0.28350407124142618 -0.73882149361721683 0
		 47.768601260708806 104.46653900739912 15.698887991063685 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_foot_root" -p "root";
	rename -uid "FF577E90-435D-7DEF-2437-51989EEFF501";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_foot_l" -p "ik_foot_root";
	rename -uid "5946C9F4-4810-2EDD-A782-E4BAF498FBD5";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 14.087671279907227 0.99425750970840454 8.2376375198364258 ;
	setAttr ".r" -type "double3" 90.044595639783211 -88.191663071784689 -81.527131053351226 ;
	setAttr ".s" -type "double3" 1 0.99999999999999978 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.0046495233472996222 0.99950197930433926 0.031211781419062105 0
		 -0.14803749178976766 0.031556184234514777 -0.98847817793877035 0 -0.98897082007369519 -2.4561468946027169e-05 0.14811048727047271 0
		 14.087671279907227 8.2376375198364258 -0.99425750970840454 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_foot_r" -p "ik_foot_root";
	rename -uid "B00FB116-4FAE-8029-E326-E49ED1DD9E6E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -14.087558746337891 0.98483455181121826 8.2382316589355469 ;
	setAttr ".r" -type "double3" -89.955404360215979 88.191663071784689 81.527131053350843 ;
	setAttr ".s" -type "double3" 1 0.99999999999999956 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.0046495233473000663 -0.99950197930433893 -0.031211781419062216 0
		 -0.14803749178978831 -0.031556184234514895 0.9884781779387668 0 -0.98897082007369175 2.4561468946471259e-05 -0.14811048727049336 0
		 -14.087558746337891 8.2382316589355469 -0.98483455181121826 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "interaction" -p "root";
	rename -uid "254C8694-4B9E-21E2-BEC2-9EAC0E42C1BD";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "center_of_mass" -p "root";
	rename -uid "4A582CD3-491A-0B5E-22C6-63A1503A1DC9";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "camera_root" -p "root";
	rename -uid "1F22F15A-467C-970B-3316-848DC2196B50";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 2.8421709430404007e-14 0 168 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 2.8421709430404007e-14 168 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "camera_bone" -p "camera_root";
	rename -uid "B9EA8EA4-4C46-4862-F8D4-6888B94FE14B";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 0 0 -3 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 2.8421709430404007e-14 165 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode transform -n "MainHero_Skirt";
	rename -uid "D9951105-45FD-961C-5245-77AB85A57166";
createNode transform -n "Skirt" -p "MainHero_Skirt";
	rename -uid "97825712-47C4-5C78-59A1-AC8CA361E9EE";
	setAttr -l on ".tx";
	setAttr -l on ".ty";
	setAttr -l on ".tz";
	setAttr -l on ".rx";
	setAttr -l on ".ry";
	setAttr -l on ".rz";
	setAttr -l on ".sx";
	setAttr -l on ".sy";
	setAttr -l on ".sz";
	setAttr ".it" no;
createNode mesh -n "SkirtShape" -p "Skirt";
	rename -uid "F8F24596-4F7B-3185-3316-C4881861616B";
	setAttr -k off ".v";
	setAttr ".vir" yes;
	setAttr ".vif" yes;
	setAttr ".uvst[0].uvsn" -type "string" "map1";
	setAttr ".cuvs" -type "string" "map1";
	setAttr ".dcc" -type "string" "Diffuse";
	setAttr ".covm[0]"  0 1 1;
	setAttr ".cdvm[0]"  0 1 1;
	setAttr ".ndt" 0;
	setAttr ".vcs" 2;
createNode mesh -n "SkirtShapeOrig" -p "Skirt";
	rename -uid "966C9649-4130-096A-B229-88B128C535F1";
	setAttr -k off ".v";
	setAttr ".io" yes;
	setAttr ".vir" yes;
	setAttr ".vif" yes;
	setAttr ".uvst[0].uvsn" -type "string" "map1";
	setAttr -s 1854 ".uvst[0].uvsp";
	setAttr ".uvst[0].uvsp[0:249]" -type "float2" 0.90966499 0.084343851 0.9166643
		 0.078458667 0.91629219 0.084507406 0.90982533 0.091349542 0.9033727 0.083812535 0.90896869
		 0.076013446 0.90333045 0.068914711 0.91662598 0.072037339 0.92422742 0.074935615
		 0.92373127 0.081136882 0.93059552 0.080484807 0.92363137 0.085053682 0.91645128 0.09098357
		 0.92372352 0.091020167 0.91688627 0.097426951 0.91034919 0.098128319 0.91748089 0.10371846
		 0.92398983 0.097129941 0.92429739 0.10336691 0.91797221 0.11003214 0.91102821 0.10472047
		 0.91167885 0.1112808 0.91826421 0.11690992 0.92373246 0.11680961 0.92323095 0.12445384
		 0.92973536 0.11778671 0.93073308 0.11055017 0.93726498 0.1110065 0.93135488 0.10368079
		 0.92425215 0.10983294 0.93152374 0.097235382 0.93901432 0.097219527 0.93916035 0.090854108
		 0.94669414 0.097116649 0.94578767 0.10404348 0.95432794 0.097284794 0.95450765 0.090247631
		 0.96152902 0.090493679 0.96097255 0.08291471 0.9683525 0.08328861 0.96774024 0.075647175
		 0.97826004 0.077732205 0.97683352 0.084803641 0.96808732 0.090946078 0.97514963 0.092141807
		 0.96698427 0.098582089 0.96098363 0.097897828 0.95947701 0.10507172 0.9653486 0.1059227
		 0.95785564 0.11195332 0.95146382 0.11132258 0.94997317 0.11808187 0.9565329 0.11857653
		 0.95544368 0.12506813 0.96227634 0.11923069 0.96370125 0.11272788 0.96956038 0.11356556
		 0.97138482 0.10675967 0.973279 0.099525869 0.96801794 0.12004763 0.96120143 0.12563193
		 0.96678531 0.12628752 0.96017659 0.1318602 0.96580857 0.13235313 0.95959473 0.1379751
		 0.95442373 0.13143241 0.94882488 0.12472057 0.94786143 0.13128525 0.95368969 0.13775539
		 0.94728047 0.13779539 0.95348138 0.14414454 0.95931667 0.1442287 0.96508771 0.1383239
		 0.96459162 0.14429617 0.95925921 0.15073258 0.96433663 0.15058917 0.95925331 0.15765655
		 0.95387501 0.15777415 0.95424473 0.16533697 0.94871527 0.16543865 0.94876939 0.17322958
		 0.94365817 0.16583622 0.94324744 0.15862155 0.93828481 0.15929842 0.93739682 0.15234834
		 0.93223518 0.15325701 0.93343848 0.16009533 0.93885458 0.16639471 0.93426079 0.16712284
		 0.93934453 0.1743325 0.94398999 0.17374694 0.94461393 0.18234223 0.94905823 0.18180376
		 0.95375687 0.18130404 0.95390946 0.17334485 0.95974237 0.18074822 0.95938718 0.17318463
		 0.9593448 0.16512191 0.96497977 0.17222369 0.96450973 0.1644845 0.96430302 0.1573301
		 0.96562892 0.18028164 0.93979406 0.18284976 0.93478614 0.17486954 0.93469995 0.1831044
		 0.93027699 0.17518693 0.92964429 0.16783559 0.92843771 0.16102695 0.92324901 0.16170573
		 0.92171222 0.15491366 0.91554958 0.15541267 0.9139666 0.14792746 0.90876716 0.15621698
		 0.9172188 0.16261792 0.91030616 0.16433156 0.91904861 0.17235053 0.92483336 0.16840494
		 0.92585766 0.17519629 0.92972451 0.18287361 0.92497009 0.18189883 0.92182308 0.176705
		 0.91975576 0.18104935 0.91259557 0.18056405 0.90754223 0.1481806 0.91299772 0.14013493
		 0.9187932 0.14069927 0.91284639 0.13244462 0.90619916 0.13954175 0.90558946 0.13236409
		 0.9055053 0.12546909 0.91250128 0.12498426 0.91821653 0.13251674 0.91818494 0.12448382
		 0.92309302 0.13236058 0.92391664 0.14026207 0.92859584 0.13223463 0.92923707 0.13931745
		 0.93504947 0.13853264 0.93601066 0.14545119 0.94144964 0.1446709 0.94243348 0.15152299
		 0.9477464 0.15089822 0.94730419 0.14420807 0.95357102 0.15074098 0.94838232 0.15800637
		 0.9410035 0.13800752 0.94133115 0.13136685 0.93508273 0.13182282 0.93539822 0.12513429
		 0.92890775 0.12510484 0.93610728 0.11818248 0.94198108 0.12466335 0.94296968 0.11799139
		 0.94443136 0.11112785 0.93843889 0.10393018 0.95300925 0.10431635 0.93066359 0.1463536
		 0.92548454 0.14742845 0.92714339 0.15423453 0.92002141 0.14807332 0.91217959 0.11794615
		 0.90555483 0.11882997 0.90534401 0.11224723 0.90469354 0.10571158 0.97774792 0.070711732
		 0.96647167 0.068535566 0.95864767 0.074684381 0.95774591 0.066162944 0.95062405 0.074456513
		 0.95360076 0.083047092 0.94404835 0.076764703 0.93910152 0.069280028 0.93511587 0.07230401
		 0.93763584 0.078662634 0.94642627 0.083654761 0.93861693 0.084592462 0.93005961 0.074927986
		 0.93108904 0.085066557 0.9314028 0.091104388 0.94696623 0.090376139 0.94380939 0.06319654
		 0.95698273 0.05815196 0.965846 0.061437964 0.96599174 0.053634822 0.97679192 0.056776345
		 0.97626317 0.049683928 0.98316866 0.050990939 0.98179924 0.057863355 0.97728652 0.063841701
		 0.98062152 0.064548135 0.97948563 0.071047008 0.98484957 0.044218063 0.9756937 0.042703211
		 0.98528963 0.037398994 0.97631711 0.03560394 0.96623039 0.038743973 0.9661082 0.046061099
		 0.96105105 0.043697417 0.95611143 0.048566878 0.97126269 0.033874154 0.97682703 0.028083384
		 0.98563325 0.030840814 0.98585105 0.024122357 0.99070477 0.025151193 0.98614579 0.017057002
		 0.9921875 0.017067015 0.99172211 0.0078226328 0.98165065 0.022433698 0.98876774 0.031350553
		 0.98673707 0.037591577 0.94979817 0.055491507 0.90376616 0.099028409 0.90305871 0.091993809
		 0.94337028 0.33883584 0.93841147 0.33846021 0.94099468 0.33293724 0.94786066 0.32292354
		 0.94240731 0.32102734 0.95014143 0.3139075 0.94376194 0.31268162 0.95122546 0.30569983
		 0.94441962 0.30498874 0.95198554 0.29833937 0.94495201 0.29770112 0.93753415 0.30438387
		 0.93736243 0.31193238 0.93113917 0.31159663 0.93122476 0.31982625 0.92587852 0.31968743
		 0.9252978 0.31172699 0.93092746 0.30411869 0.92482704 0.30426252 0.93099779 0.29682195
		 0.93775004 0.29721111 0.93829787 0.2900362 0.94561833 0.29054666 0.94650984 0.28331041
		 0.93924397 0.28280878 0.94746298 0.27590185 0.94033974 0.27557909 0.94826138 0.26834559
		 0.94119865 0.26829284 0.94180512 0.26100707 0.93467307 0.2611891 0.93526763 0.25410938
		 0.92838675 0.2540952 0.92901134 0.24709952 0.92241037 0.24689108 0.92297959 0.24027139
		 0.91687286 0.23980778;
	setAttr ".uvst[0].uvsp[250:499]" 0.91690743 0.23389953 0.91120535 0.23935688
		 0.91157544 0.24593645 0.90560007 0.23944271 0.90482581 0.23304337 0.89886755 0.23272872
		 0.89901775 0.22578788 0.89267641 0.2319783 0.8932023 0.2397995 0.88647366 0.23900098
		 0.88648146 0.23063296 0.89319211 0.22420275 0.88741833 0.22238374 0.88003749 0.22915137
		 0.87975097 0.23778576 0.87255502 0.23688066 0.872509 0.24510896 0.86457646 0.24528027
		 0.86417586 0.23680913 0.86451417 0.22759813 0.85376805 0.22827721 0.85265386 0.21848339
		 0.86498839 0.21776742 0.86257553 0.20814645 0.85155022 0.2076773 0.86153966 0.19943178
		 0.87025386 0.19934922 0.8680985 0.18952107 0.85993963 0.18947947 0.84976977 0.19175136
		 0.84851366 0.18268192 0.85932487 0.18207407 0.84681284 0.17149782 0.85074919 0.19991374
		 0.87852907 0.19965065 0.87083465 0.20851684 0.87853801 0.21017069 0.87498957 0.21881032
		 0.88131046 0.22049922 0.87304837 0.22800541 0.88397801 0.21210182 0.88947892 0.21354544
		 0.88731587 0.20222497 0.88261503 0.20193839 0.89249521 0.20284915 0.89801848 0.20934588
		 0.89497215 0.21697235 0.90320385 0.21377796 0.90051097 0.21947849 0.90593952 0.22163653
		 0.9078114 0.21677482 0.91230971 0.21881711 0.91147417 0.2230612 0.90492398 0.22705245
		 0.91093409 0.22801089 0.91701746 0.2235961 0.91696507 0.21941555 0.9229722 0.22318363
		 0.92328817 0.22843874 0.929914 0.22770339 0.92996818 0.23382539 0.93696076 0.23315036
		 0.93654162 0.23996627 0.94370961 0.23952436 0.9429369 0.24665725 0.95017809 0.24663806
		 0.94940448 0.253636 0.95637918 0.25414777 0.95732397 0.24728334 0.95113266 0.23945129
		 0.95850271 0.24002129 0.9518584 0.23195672 0.95962423 0.23176277 0.95181859 0.22409737
		 0.95935035 0.22212112 0.95133817 0.21538967 0.94360858 0.21796715 0.94311637 0.21142972
		 0.93503457 0.21374208 0.93614572 0.21998638 0.92798078 0.2163868 0.92931646 0.22183841
		 0.92214173 0.2183907 0.93686104 0.22650319 0.94416749 0.22526968 0.94422615 0.23242176
		 0.95982468 0.20200616 0.95571965 0.26119828 0.94885117 0.26088262 0.95514005 0.26871532
		 0.9544459 0.27643573 0.94228798 0.25380427 0.93589723 0.24696887 0.92959434 0.24027467
		 0.92323786 0.23408604 0.91695613 0.228486 0.9108727 0.23343492 0.85492516 0.23753172
		 0.85601687 0.24606675 0.85693556 0.25392288 0.86520272 0.25297284 0.85774505 0.26113653
		 0.86581862 0.26027846 0.85853761 0.26795352 0.86616707 0.26736712 0.8593598 0.27467799
		 0.86636931 0.27426958 0.87278664 0.26750398 0.87268299 0.26020688 0.87929422 0.26789677
		 0.87930489 0.27484632 0.88702989 0.27505648 0.88702458 0.28177798 0.89514267 0.28203928
		 0.89450532 0.2889241 0.90147179 0.28957731 0.90052915 0.29661202 0.90630889 0.2901479
		 0.90669841 0.28258789 0.91058081 0.29039496 0.91013241 0.2979902 0.90561783 0.29750633
		 0.90980893 0.30519003 0.91462797 0.29790795 0.91477597 0.29029155 0.91941309 0.29720056
		 0.91944015 0.30480826 0.92475325 0.29673576 0.9252491 0.28921133 0.93165112 0.28966033
		 0.93249458 0.28248835 0.9259091 0.28218496 0.92655897 0.27521932 0.92042994 0.27508485
		 0.92101556 0.26794314 0.91608429 0.26769805 0.92142206 0.26083219 0.92719632 0.26820135
		 0.92781168 0.26118016 0.92184782 0.25376946 0.91629976 0.26047879 0.91636711 0.25326872
		 0.91663504 0.24633151 0.91176426 0.25309825 0.9117856 0.26035511 0.90707397 0.25328076
		 0.90657282 0.24617624 0.90110886 0.24677205 0.89986742 0.2398479 0.89399493 0.24713582
		 0.90187317 0.25375366 0.89466107 0.25428724 0.90212524 0.26085079 0.90722144 0.26048028
		 0.90711451 0.2677142 0.91160858 0.26759946 0.91135466 0.27498901 0.91563356 0.27502316
		 0.91516715 0.28258824 0.91982645 0.2823205 0.91949898 0.28960043 0.91094011 0.28267574
		 0.90699226 0.27502954 0.90214455 0.27512157 0.90217078 0.26798344 0.89528334 0.2682296
		 0.89508647 0.26129019 0.8869372 0.26129067 0.88695496 0.25422466 0.8795138 0.25344121
		 0.87963921 0.24590242 0.87260014 0.25275409 0.87936491 0.26074755 0.8867808 0.2468856
		 0.88695651 0.26819831 0.89539349 0.27516979 0.90196151 0.28233093 0.93407017 0.26832128
		 0.93329775 0.27539361 0.91990024 0.31211841 0.91459465 0.31256545 0.91503352 0.31960046
		 0.90941805 0.31924713 0.90921998 0.32591748 0.9035365 0.32498932 0.90279144 0.33118582
		 0.89787745 0.32415605 0.90392983 0.31842524 0.89827013 0.31747246 0.90436077 0.3115468
		 0.89877158 0.31057101 0.90492392 0.30456722 0.90952128 0.31233299 0.9144662 0.30532598
		 0.89951026 0.30360955 0.89267707 0.30966318 0.89242429 0.31666934 0.88651317 0.31614161
		 0.89228046 0.32354772 0.89745224 0.33055854 0.89209217 0.33026546 0.88667083 0.32321322
		 0.88675547 0.33019567 0.88105798 0.32310838 0.88055986 0.31593728 0.87543255 0.32320219
		 0.88143331 0.33032799 0.87604606 0.33059257 0.86983132 0.32341951 0.87463558 0.3159675
		 0.86879873 0.31605983 0.87383735 0.30890119 0.86787671 0.30887473 0.87324572 0.30201656
		 0.87963563 0.30198038 0.87293237 0.29514396 0.8672843 0.30185616 0.86707371 0.29485089
		 0.8728382 0.28821981 0.87940288 0.29512823 0.87930977 0.28833532 0.87279201 0.28136927
		 0.8669185 0.28792489 0.86667579 0.28109938 0.86063838 0.2880047 0.86104286 0.29475713
		 0.86147726 0.30170608 0.86011016 0.28136414 0.87282079 0.27454698 0.87927198 0.28159189
		 0.88685721 0.28848553 0.88658363 0.29524088 0.89379168 0.29574186 0.89310664 0.30265391
		 0.88641775 0.30216992 0.8863979 0.30909818 0.88001776 0.30887902 0.8620711 0.30886924
		 0.86295652 0.31622487 0.86422026 0.32381129 0.86567664 0.33136797 0.87067735 0.33096963
		 0.90821427 0.33225042 0.91495746 0.32680511 0.91355413 0.3337307 0.92045629 0.32764554
		 0.92050219 0.31962657 0.92588675 0.32835555 0.91914093 0.33553749 0.92527103 0.33715534;
	setAttr ".uvst[0].uvsp[500:749]" 0.93122464 0.32865155 0.93677872 0.3201344
		 0.93657535 0.33099115 0.93185353 0.33744335 0.95361638 0.2839787 0.95276403 0.29123414
		 0.45772445 0.28711319 0.47046852 0.29216421 0.46029037 0.29414082 0.44850317 0.28991997
		 0.44506466 0.28302479 0.45279399 0.27985513 0.46073258 0.27598137 0.45375866 0.26867324
		 0.46665657 0.27058268 0.45856652 0.26386034 0.44581395 0.26222181 0.44137037 0.26673698
		 0.43685973 0.25843966 0.44942921 0.25732517 0.43952703 0.25250208 0.42970365 0.25001401
		 0.42803544 0.25700998 0.41999671 0.24924999 0.41998574 0.25686681 0.41145524 0.24997276
		 0.41241786 0.25772166 0.42012239 0.26451516 0.42714778 0.26387632 0.42724025 0.27143395
		 0.4332535 0.27060258 0.4349384 0.27796865 0.43808472 0.27072251 0.43425739 0.26424587
		 0.44757852 0.27282023 0.44105667 0.27597022 0.43761578 0.28514683 0.42857364 0.27923119
		 0.43047696 0.28660011 0.42204455 0.28026605 0.42080721 0.27241254 0.41420361 0.27364647
		 0.41323426 0.26566541 0.40642056 0.26714516 0.40748659 0.27506703 0.39963001 0.26870155
		 0.39837357 0.26087308 0.39160919 0.26244509 0.39013356 0.25483739 0.38345659 0.25623691
		 0.38483161 0.26384783 0.3928574 0.27016985 0.3860358 0.27150333 0.37787807 0.26521975
		 0.37638405 0.25756925 0.36901847 0.25912923 0.3707656 0.2668125 0.37911594 0.27281535
		 0.37208191 0.27434331 0.36366233 0.26883709 0.36158946 0.26122832 0.35445869 0.26381427
		 0.35676298 0.2712962 0.36502492 0.27629924 0.35794106 0.2786653 0.35009739 0.2739867
		 0.34789234 0.26667297 0.34242076 0.26928496 0.34361961 0.27654004 0.35070568 0.28123033
		 0.34283775 0.28312856 0.33726534 0.27776778 0.33573839 0.28387237 0.33085129 0.27832854
		 0.32967535 0.28433204 0.32407132 0.27933192 0.32410291 0.27506369 0.31680766 0.28015023
		 0.32369441 0.28495765 0.31663123 0.28552234 0.308992 0.28016281 0.31700712 0.27545261
		 0.3094745 0.2750085 0.30085257 0.2795769 0.30060899 0.28542447 0.29243171 0.28513038
		 0.29263371 0.29151654 0.28478301 0.29175377 0.28521347 0.2982899 0.27768171 0.29871488
		 0.27807087 0.30558312 0.28557464 0.30494022 0.29290795 0.29802954 0.29320702 0.30453193
		 0.28609291 0.31168127 0.29361629 0.3111136 0.30087256 0.30415636 0.30119202 0.31059623
		 0.30168411 0.31707704 0.30922616 0.31643701 0.30979526 0.32283813 0.31734544 0.32203305
		 0.31796673 0.32836282 0.32507738 0.32746702 0.32573104 0.33381855 0.33235177 0.33289009
		 0.33319759 0.33923137 0.33902684 0.33172804 0.33997992 0.33790725 0.34106541 0.34412491
		 0.3481822 0.34269011 0.34918776 0.34903038 0.34217465 0.35039914 0.3502371 0.35545278
		 0.3432973 0.35672259 0.35137895 0.36198014 0.34447986 0.36307144 0.34573528 0.36948025
		 0.338718 0.37068862 0.34015661 0.37711561 0.33202749 0.3719734 0.33374038 0.37851584
		 0.341537 0.3836717 0.34697506 0.3759625 0.34807533 0.38252103 0.35374501 0.37541234
		 0.35257331 0.36867785 0.35918874 0.36834335 0.3580603 0.36136901 0.35709095 0.35452771
		 0.36376879 0.35427999 0.363213 0.34742665 0.37005329 0.34752369 0.3704206 0.3543421
		 0.36452168 0.36122108 0.3710987 0.36117089 0.3774161 0.35442984 0.37717152 0.34781647
		 0.38437399 0.34787166 0.3845512 0.35439539 0.37795308 0.36108744 0.38490644 0.3609463
		 0.3918964 0.36074626 0.39200926 0.36758459 0.39869127 0.36740887 0.39849836 0.37471282
		 0.4049904 0.37432814 0.40477297 0.38184607 0.39841029 0.3822242 0.3920767 0.37489247
		 0.39209676 0.38243735 0.38586831 0.3825469 0.39207143 0.39002275 0.39838532 0.38973808
		 0.3984277 0.39704239 0.39207873 0.39739347 0.38589612 0.39022911 0.38580942 0.39772356
		 0.3798649 0.39025974 0.37979403 0.38253218 0.38571358 0.37497699 0.37937784 0.37501156
		 0.38535216 0.36773789 0.37867939 0.36789048 0.37302944 0.375121 0.37371543 0.38250202
		 0.36765817 0.38250196 0.36795512 0.38994849 0.36186245 0.38943046 0.36165679 0.39688683
		 0.35549524 0.39603651 0.35483271 0.40388876 0.34937751 0.40388274 0.34860301 0.41209888
		 0.34312549 0.41222447 0.34206778 0.4204306 0.33744651 0.41248018 0.33771548 0.40513659
		 0.33148655 0.40588844 0.33170772 0.41303337 0.32536566 0.40703785 0.32613015 0.41403532
		 0.33152157 0.42130041 0.33676824 0.42078328 0.33620566 0.42911959 0.33089653 0.429699
		 0.33643183 0.43587309 0.34222582 0.43483186 0.34170875 0.42832375 0.34732553 0.42749637
		 0.34756285 0.42022741 0.35327542 0.4198826 0.35393015 0.41207337 0.35966167 0.41220623
		 0.36062908 0.40456295 0.36674437 0.40513062 0.36759484 0.39755774 0.37359464 0.39782929
		 0.37390944 0.39016163 0.37962577 0.39788187 0.37293372 0.40525556 0.37920812 0.40512753
		 0.38563013 0.40480256 0.38548455 0.41138697 0.37889645 0.41183436 0.37234688 0.41219044
		 0.37205341 0.41862607 0.36592105 0.41233134 0.36546388 0.41906893 0.36555576 0.42531896
		 0.35924336 0.42602909 0.35986373 0.43216693 0.35374457 0.43301135 0.35317573 0.42675436
		 0.35918024 0.41945893 0.34792039 0.43388891 0.36612147 0.43131244 0.37217247 0.4246437
		 0.37267449 0.43045449 0.3788878 0.42397404 0.37874487 0.41809905 0.38544151 0.41754866
		 0.39215907 0.41701549 0.39228123 0.42290246 0.38562062 0.4233743 0.38592675 0.4290067
		 0.37927341 0.42963368 0.39245334 0.4285804 0.39887232 0.42255545 0.39893925 0.42837781
		 0.40541983 0.42238033 0.40535453 0.4163717 0.41191807 0.42226732 0.41186193 0.42825615
		 0.4182286 0.42829359 0.41831031 0.42220008 0.41186374 0.41620278 0.4182747 0.41608959
		 0.41170612 0.40997434 0.40522078 0.41017818 0.40498534 0.40368062 0.39867237 0.41045761
		 0.39877427 0.41660833 0.39209989 0.41087425 0.39209652 0.40435582 0.39854518 0.40396678
		 0.4047938 0.39673376 0.41145056 0.40345347 0.41109392 0.39639795 0.40470254 0.38940442;
	setAttr ".uvst[0].uvsp[750:999]" 0.41092563 0.38894254 0.41105905 0.38123834
		 0.41701636 0.38831037 0.41722974 0.39594859 0.42320749 0.39540005 0.4238722 0.40279567
		 0.42993873 0.40215051 0.43061653 0.4091534 0.42431793 0.40955746 0.41775906 0.40315855
		 0.41811651 0.40980214 0.42456028 0.41597521 0.43079561 0.41578001 0.43059245 0.42219603
		 0.42454141 0.42216605 0.43028051 0.42843616 0.4357734 0.42866719 0.43625957 0.42234659
		 0.44092259 0.42904532 0.44147795 0.42267382 0.43662322 0.41554642 0.43656173 0.40840477
		 0.44203201 0.41540372 0.44204736 0.40732878 0.43581548 0.40094686 0.44167888 0.39954054
		 0.43501151 0.39361465 0.42907998 0.3947323 0.42905167 0.38707459 0.43517235 0.3864491
		 0.42997894 0.37936389 0.42374715 0.37992764 0.42496204 0.37231731 0.41822636 0.37301666
		 0.41740581 0.38054132 0.41156998 0.373703 0.40540391 0.36703432 0.41224355 0.36641377
		 0.40580958 0.3600114 0.39884895 0.36046267 0.39890379 0.35380304 0.39174476 0.35417897
		 0.39160222 0.34765172 0.38429913 0.34122795 0.39149117 0.3410356 0.38417849 0.3345108
		 0.37710837 0.34118909 0.36995214 0.34086096 0.37703544 0.33451873 0.36978957 0.33437514
		 0.36270073 0.34083974 0.35624248 0.34790635 0.35543382 0.34153444 0.34721974 0.33649206
		 0.354698 0.33532608 0.36226389 0.33452559 0.36172509 0.32838798 0.35398421 0.32918727
		 0.34630901 0.3303833 0.34548053 0.32433796 0.33820921 0.3256008 0.33749372 0.31950641
		 0.33161715 0.32663071 0.33096066 0.32043386 0.32445878 0.32121819 0.32391781 0.3150875
		 0.33040887 0.31438541 0.3235299 0.30905432 0.31650922 0.30955184 0.31650549 0.303397
		 0.30865079 0.30375528 0.30859023 0.2975086 0.30065778 0.29776549 0.30856171 0.29141837
		 0.31651679 0.29128146 0.30870527 0.28565133 0.30055544 0.29150331 0.32342249 0.29107362
		 0.3232483 0.29716086 0.32933506 0.296754 0.32963997 0.30261523 0.33534664 0.29581797
		 0.33587274 0.30172026 0.32997745 0.30847031 0.32329702 0.30310547 0.33640492 0.30760038
		 0.33692211 0.31351382 0.34412056 0.31236458 0.34476143 0.3183375 0.3526828 0.31709814
		 0.35329947 0.32311875 0.36060402 0.31614518 0.36114958 0.32229954 0.36835822 0.31544089
		 0.36887333 0.3217169 0.36938289 0.32800579 0.37634 0.32143396 0.37585571 0.3149817
		 0.38315138 0.31459922 0.38361302 0.3212018 0.3767629 0.32791501 0.38396579 0.32782328
		 0.39136314 0.33430529 0.39115626 0.32755041 0.39851975 0.33373135 0.39869162 0.34055686
		 0.39881507 0.34723639 0.40600508 0.34657043 0.40602514 0.3532455 0.4132019 0.35244638
		 0.41284236 0.35932374 0.42011595 0.3584764 0.41921863 0.36566204 0.42626888 0.36482805
		 0.43148971 0.37182045 0.43319619 0.36428803 0.42731529 0.35743058 0.4345257 0.35658288
		 0.44001386 0.36420226 0.43828052 0.37182069 0.44480446 0.37192386 0.44318932 0.37921464
		 0.43646848 0.37914819 0.44191736 0.38589275 0.44850922 0.38583422 0.4479301 0.39215589
		 0.44154304 0.39247167 0.44746149 0.3990525 0.45272398 0.3997581 0.44697669 0.4068954
		 0.45173243 0.40721172 0.45773429 0.40076351 0.4585802 0.39363015 0.45357814 0.39276487
		 0.45934123 0.38664794 0.46480986 0.38767773 0.46612385 0.38088584 0.46022037 0.37971801
		 0.46761912 0.37411022 0.46151379 0.37270468 0.45613185 0.37196523 0.46356907 0.36557287
		 0.45815095 0.36429101 0.45248833 0.36393571 0.45477387 0.35591054 0.448349 0.35589868
		 0.45021901 0.34794289 0.44285011 0.34840202 0.441522 0.35619926 0.43531841 0.34901381
		 0.43571639 0.34198529 0.42783645 0.34304816 0.42781419 0.35012448 0.42052466 0.34440035
		 0.42019334 0.33743405 0.41304967 0.33882296 0.41275868 0.33178586 0.40566954 0.33290255
		 0.40542617 0.3259213 0.39828983 0.3268888 0.39796931 0.32005 0.39080614 0.32080978
		 0.39033571 0.31407857 0.38262269 0.30799592 0.38978317 0.30735636 0.39746502 0.31321299
		 0.39689684 0.30644971 0.38915163 0.30059016 0.38203454 0.30129552 0.38142636 0.29447007
		 0.37481937 0.30197328 0.3753536 0.30851519 0.36785945 0.30914813 0.3673566 0.30282873
		 0.35957417 0.30389202 0.35911122 0.297782 0.35100538 0.29914743 0.351522 0.305107
		 0.3428801 0.30051649 0.34350696 0.30642951 0.3520954 0.31109428 0.3600772 0.31000888
		 0.34235409 0.29463524 0.3351191 0.28989577 0.3422778 0.28892285 0.35059246 0.2932598
		 0.35050067 0.28734469 0.35872364 0.29164886 0.36685976 0.29646289 0.36634481 0.2900148
		 0.35839084 0.28536022 0.36578673 0.28335881 0.3736707 0.28857261 0.37425372 0.29534537
		 0.38079938 0.28747427 0.37300125 0.28160965 0.38007703 0.28025651 0.38779345 0.28649306
		 0.3884832 0.29364431 0.39549983 0.29265928 0.39623016 0.29962611 0.40336692 0.29847658
		 0.40408745 0.3053447 0.40467429 0.31212896 0.41201171 0.31091434 0.41234726 0.31772202
		 0.41987318 0.31668603 0.41987538 0.32356364 0.42778754 0.32254207 0.42780679 0.32935733
		 0.43611211 0.32827365 0.43600464 0.33510661 0.44447431 0.33405435 0.44387707 0.34106648
		 0.45186281 0.34039742 0.45732623 0.34808999 0.45959878 0.34001321 0.45276141 0.33301103
		 0.46069586 0.33229232 0.45309544 0.32547861 0.44460186 0.32695723 0.44454062 0.3198024
		 0.43605375 0.32131952 0.4357484 0.31432354 0.42761999 0.31563938 0.4271436 0.30872881
		 0.41953021 0.30980933 0.41879338 0.30297935 0.41139582 0.30413538 0.41056135 0.29724717
		 0.40253592 0.29144663 0.40959102 0.29015195 0.40165389 0.28415763 0.39473283 0.28541303
		 0.39387313 0.2778815 0.38700047 0.27909815 0.40069482 0.2765227 0.4085443 0.28278029
		 0.41535258 0.28144169 0.41658062 0.28890115 0.42352819 0.28775275 0.42500961 0.29490268
		 0.43239775 0.29367083 0.4339253 0.3005411 0.44217628 0.29890347 0.44349736 0.30571377
		 0.45236921 0.3036561 0.45305651 0.31077349 0.46220607 0.30880189 0.46198553 0.31644797;
	setAttr ".uvst[0].uvsp[1000:1249]" 0.4532364 0.31806421 0.44423237 0.31268013
		 0.46135169 0.32417393 0.46923414 0.32419282 0.46809375 0.33247995 0.47604802 0.32567358
		 0.47031116 0.31598628 0.47766146 0.31688505 0.47108445 0.30744886 0.46168458 0.30128396
		 0.47109303 0.29961085 0.45084023 0.29671919 0.47907135 0.3080349 0.48015589 0.29952717
		 0.48609474 0.30938649 0.48423159 0.31845748 0.4933559 0.31091273 0.4958064 0.30241388
		 0.50182933 0.31170487 0.49840882 0.32226455 0.49085563 0.32022583 0.48841479 0.32954526
		 0.48217461 0.3275317 0.4798989 0.33627355 0.47420701 0.33423138 0.47207382 0.34298074
		 0.46632981 0.34094727 0.46379486 0.34914893 0.46952859 0.35130453 0.46641499 0.35854316
		 0.46089038 0.35670835 0.46940911 0.36748612 0.4718225 0.36070621 0.47768497 0.36217123
		 0.48012733 0.35473669 0.47463492 0.35306555 0.4829748 0.34683579 0.48930714 0.34911728
		 0.49212468 0.34079504 0.48578158 0.3384248 0.47735319 0.34481943 0.49520627 0.33179343
		 0.48676986 0.35680717 0.48450321 0.36388946 0.4824343 0.37060708 0.47574389 0.36902463
		 0.48047742 0.37727571 0.47401631 0.37564933 0.47235522 0.38232058 0.4786081 0.38397402
		 0.47081745 0.38909447 0.46372676 0.39463079 0.46937573 0.39590788 0.47684374 0.39068758
		 0.47515777 0.39753473 0.47339132 0.40455717 0.46788764 0.4028939 0.47133958 0.41172719
		 0.46633783 0.41008365 0.46167576 0.40891105 0.4605723 0.41621149 0.45618048 0.41544741
		 0.45535877 0.42313552 0.4512333 0.42293149 0.45040739 0.43044299 0.44576526 0.42963779
		 0.44645876 0.42298096 0.4512555 0.41516751 0.44672036 0.41530585 0.45399117 0.43119419
		 0.45915544 0.42396247 0.45734051 0.43199432 0.46275598 0.42495304 0.46469417 0.41732955
		 0.46618733 0.42631847 0.46061349 0.43281084 0.4635677 0.43361723 0.46890464 0.4189595
		 0.45693052 0.40799725 0.46268889 0.40171695 0.50415629 0.30408132 0.50645423 0.2960698
		 0.49858457 0.29457998 0.50096738 0.28658223 0.49007437 0.29230833 0.49156421 0.28552687
		 0.48085544 0.2846579 0.48196152 0.27893847 0.47427943 0.27592188 0.46892649 0.28344852
		 0.48073852 0.29145837 0.48796466 0.30059528 0.49210262 0.27966762 0.50176853 0.27856982
		 0.50896412 0.28722364 0.51219833 0.2763772 0.43507102 0.30739033 0.44015387 0.29210019
		 0.42625374 0.30183291 0.41777772 0.29605246 0.42780849 0.33611542 0.41992965 0.33049786
		 0.41251892 0.32470441 0.40511018 0.31895041 0.40585297 0.33981514 0.41324744 0.34566623
		 0.42056349 0.35144293 0.44653711 0.36413926 0.45085946 0.37188125 0.44950706 0.3791796
		 0.45491773 0.37924123 0.45413083 0.38610965 0.32922611 0.29063839 0.31649619 0.29731131
		 0.30883476 0.31008017 0.31684822 0.31577241 0.42307663 0.38768238 0.42440081 0.42834198
		 0.40542436 0.42828393 0.33028236 0.43710244 0.32532629 0.43004715 0.32625043 0.42184365
		 0.32066238 0.42221856 0.32001841 0.43010104 0.31445011 0.422791 0.31533495 0.43082941
		 0.30884585 0.42424178 0.31093243 0.43214458 0.31674993 0.4401238 0.32035834 0.43928576
		 0.31338036 0.44087362 0.30709338 0.43398654 0.30409509 0.42652446 0.31019726 0.44159949
		 0.30145472 0.41951895 0.30723047 0.41736412 0.29915208 0.41286111 0.30570278 0.41088533
		 0.31249541 0.40980804 0.31153485 0.40334558 0.31802458 0.40211225 0.31678799 0.39568001
		 0.32446638 0.40056205 0.32344571 0.39422107 0.33096614 0.39931262 0.33014286 0.39288282
		 0.33737591 0.39836133 0.33654317 0.39170951 0.34355187 0.3971622 0.34270132 0.39034158
		 0.33531702 0.38510334 0.32892746 0.38646793 0.32732791 0.38005805 0.32546556 0.37360895
		 0.31883952 0.37535524 0.3169598 0.36892855 0.32365593 0.36718535 0.33042747 0.36560416
		 0.32216787 0.36073232 0.32913774 0.35930741 0.33739996 0.36433643 0.33623824 0.35810959
		 0.33514687 0.3518334 0.3281053 0.35300434 0.32719731 0.34664071 0.33412024 0.34554338
		 0.32643506 0.34023106 0.31931251 0.34125423 0.31860882 0.33477026 0.31127009 0.33578771
		 0.31211075 0.34238982 0.32009196 0.34779024 0.31302238 0.34905958 0.32101691 0.35430729
		 0.31403321 0.35577357 0.31530362 0.36242735 0.30718213 0.35716224 0.30851227 0.36398298
		 0.31015971 0.37062168 0.31199419 0.37702072 0.30499825 0.3786841 0.30678922 0.38486499
		 0.3137874 0.38327348 0.30852544 0.39094037 0.29952812 0.38661885 0.2978195 0.38042575
		 0.29050457 0.38237715 0.28900391 0.37580025 0.29618016 0.37393534 0.28760502 0.36887038
		 0.29466754 0.36712039 0.30323881 0.37223554 0.30164999 0.3654958 0.29327637 0.36001813
		 0.28624836 0.36151648 0.28500497 0.35402679 0.29201266 0.35280383 0.2838026 0.34662211
		 0.2908352 0.34564793 0.29900867 0.35156965 0.30024922 0.35856152 0.30601621 0.35031843
		 0.29787642 0.34460431 0.30496433 0.34350914 0.29682833 0.33773625 0.30400273 0.33677894
		 0.29586479 0.33100665 0.30313119 0.33014822 0.31049117 0.32927626 0.30234021 0.32358611
		 0.29496741 0.32435882 0.29420501 0.31774342 0.28683382 0.3185029 0.27865517 0.31253809
		 0.27954981 0.31951088 0.28771591 0.32521236 0.28057864 0.32624108 0.28869596 0.33187592
		 0.28162682 0.33277631 0.28973669 0.33864903 0.28268656 0.33950174 0.29206964 0.3886621
		 0.30123246 0.39264441 0.29369876 0.39472693 0.30287716 0.39854729 0.31020972 0.39702153
		 0.31541294 0.3894521 0.30433813 0.40448129 0.29538822 0.40067351 0.29715055 0.40661621
		 0.32062772 0.38168818 0.32217878 0.38795269 0.34893566 0.38921452 0.35475421 0.38212651
		 0.35539439 0.38895488 0.36138102 0.38231277 0.36040115 0.37531805 0.36674082 0.37527812
		 0.36556491 0.36821914 0.37203419 0.3680464 0.34942946 0.39616024 0.34376454 0.40444076
		 0.31920049 0.40855706 0.31357545 0.41617095 0.32034796 0.41520607 0.32538337 0.43813109
		 0.27722228 0.29213941 0.28420112 0.28517199 0.27638334 0.28568697 0.28350735 0.27832234;
	setAttr ".uvst[0].uvsp[1250:1499]" 0.29238185 0.27887809 0.29255879 0.27276647
		 0.28221762 0.2690618 0.27453828 0.27767491 0.27029306 0.26944625 0.30138302 0.27394104
		 0.33082014 0.27381682 0.3372263 0.27166265 0.39672628 0.2532075 0.40522498 0.25921214
		 0.40377605 0.25142717 0.74508178 0.39109027 0.74510878 0.39821637 0.74314368 0.39610821
		 0.74008435 0.39784276 0.74204713 0.39064348 0.73865706 0.39061922 0.74104929 0.38354397
		 0.74426937 0.38362432 0.74375647 0.37681234 0.74063087 0.37656391 0.74377942 0.3699832
		 0.74723524 0.37714463 0.74709636 0.37034744 0.74412602 0.3631351 0.74104577 0.36281753
		 0.7415368 0.35603094 0.73751593 0.36248577 0.73735839 0.36936045 0.73191357 0.36861682
		 0.73240095 0.37573332 0.72564173 0.37598038 0.72684425 0.38362831 0.73326999 0.38311684
		 0.73736054 0.37619495 0.73759484 0.38333225 0.74072236 0.36967182 0.73441452 0.39049029
		 0.73568499 0.39775646 0.72971261 0.39786524 0.73033619 0.40348256 0.7365191 0.40298784
		 0.74164009 0.40190727 0.74307257 0.40579009 0.74667388 0.39875984 0.74770814 0.4068988
		 0.74293339 0.41513979 0.7377252 0.41403127 0.73677808 0.40760225 0.73028606 0.4091875
		 0.73374397 0.41781402 0.74231863 0.42298102 0.75032973 0.41591001 0.75095063 0.42392886
		 0.75647694 0.41780454 0.7577768 0.41279936 0.7566762 0.40655541 0.74921727 0.39916623
		 0.75605953 0.39982265 0.76420039 0.4059763 0.76381272 0.39959717 0.76367807 0.39312065
		 0.76779628 0.39907676 0.7678566 0.405402 0.77014363 0.40504539 0.7697404 0.41146302
		 0.77345151 0.41114736 0.77314031 0.41715461 0.76948965 0.4174484 0.76813996 0.41195083
		 0.76818985 0.41797477 0.76929951 0.42241591 0.77265203 0.42283893 0.76834017 0.42257321
		 0.7644763 0.4184339 0.76461661 0.41246563 0.76466423 0.42294097 0.75664884 0.42358339
		 0.77850288 0.42339516 0.77927279 0.41664469 0.78055614 0.42349124 0.78132474 0.41658401
		 0.78005779 0.41043001 0.77395695 0.40495843 0.78055775 0.40434086 0.7744782 0.39882123
		 0.77041054 0.39877415 0.77096987 0.39264107 0.76773435 0.3928628 0.76811796 0.38643122
		 0.76393843 0.38667238 0.76433349 0.37979484 0.76856327 0.37969428 0.76468039 0.37309837
		 0.75712585 0.37199569 0.75792497 0.36522436 0.75065714 0.37086725 0.75046831 0.37766075
		 0.75650591 0.37859988 0.75015467 0.38452232 0.74737889 0.38398069 0.74757385 0.39129871
		 0.75002569 0.39162093 0.75590962 0.39254075 0.75609416 0.38531983 0.75098747 0.3640427
		 0.74737012 0.36354029 0.75164318 0.35724282 0.75897568 0.35840917 0.75992364 0.35168356
		 0.75237584 0.35039693 0.76099753 0.34499502 0.76835203 0.34628427 0.76246697 0.33837926
		 0.75500655 0.33693659 0.75675458 0.3303563 0.7519809 0.3294003 0.75345361 0.32277632
		 0.74744207 0.32850933 0.74680018 0.33545256 0.74267262 0.32830584 0.7426337 0.32134587
		 0.73680449 0.32838845 0.73737782 0.33531451 0.73008096 0.33527362 0.73065001 0.34189129
		 0.72220111 0.34214604 0.72263241 0.34854853 0.73112917 0.34852052 0.73773199 0.34218502
		 0.73778594 0.34900153 0.73148209 0.35513961 0.72316468 0.3549751 0.72382712 0.36149919
		 0.73183185 0.3617816 0.7376889 0.3556838 0.72461921 0.36830282 0.74196118 0.34924519
		 0.74246711 0.34228915 0.74538571 0.34952521 0.74478394 0.356354 0.74808657 0.35676146
		 0.74870735 0.34989917 0.74608612 0.3424952 0.74956423 0.34298849 0.753465 0.34362972
		 0.75070989 0.33612263 0.74269629 0.33526373 0.72182727 0.33562666 0.72928363 0.32839453
		 0.72142333 0.32871902 0.72863251 0.32122672 0.73616797 0.32124841 0.73573875 0.31390142
		 0.74276227 0.31429636 0.74330771 0.30729425 0.74920827 0.31496567 0.74823248 0.32170284
		 0.75517201 0.31612927 0.7585144 0.32370472 0.76035488 0.31702816 0.76526606 0.32499886
		 0.76667494 0.31838679 0.76218152 0.3103292 0.75689685 0.30947077 0.75859636 0.30272818
		 0.75171739 0.30156422 0.75345385 0.29472005 0.76047099 0.29591435 0.76383877 0.3035332
		 0.76554894 0.29675651 0.76941866 0.30473298 0.76807809 0.31166399 0.7736904 0.30584311
		 0.77483749 0.2987349 0.77741176 0.29939789 0.778678 0.29197419 0.77996159 0.29999149
		 0.77905554 0.30712575 0.78261107 0.30064833 0.78367019 0.29313481 0.78680617 0.30114079
		 0.78178579 0.30776268 0.78614402 0.30848932 0.78130817 0.31479406 0.77834016 0.31418335
		 0.77785891 0.32089365 0.77485222 0.32030785 0.77414215 0.32681048 0.77736372 0.32738101
		 0.78111029 0.32150757 0.78061682 0.32806635 0.77676368 0.33393884 0.78009558 0.33462232
		 0.77614439 0.34046435 0.77343631 0.33336353 0.77277368 0.34006119 0.77203268 0.34679103
		 0.77549142 0.34723079 0.77485633 0.35386872 0.77887267 0.34772456 0.77839136 0.35428262
		 0.774158 0.36040938 0.77121782 0.35344911 0.77042085 0.36008245 0.77337515 0.36676824
		 0.77786458 0.36077416 0.77731365 0.36711431 0.78367114 0.36747015 0.78319609 0.37344241
		 0.78524196 0.37336946 0.7846539 0.37969488 0.78252727 0.37975824 0.78411943 0.38609558
		 0.78822291 0.38579273 0.78770298 0.39179552 0.79109764 0.39184153 0.79017222 0.39764333
		 0.79452276 0.39773285 0.79330164 0.40358591 0.79982048 0.40350091 0.79830939 0.40924633
		 0.80454034 0.41010964 0.80274612 0.41567254 0.81175983 0.41182089 0.80977452 0.41721296
		 0.81858021 0.41393709 0.82021868 0.40850836 0.82575756 0.41022754 0.82701671 0.4042117
		 0.82187492 0.40257299 0.82868087 0.39781088 0.83501482 0.39984608 0.83661824 0.39282191
		 0.8439877 0.39486593 0.8457281 0.38681799 0.83797693 0.38533694 0.83034366 0.39095497
		 0.83136517 0.38387781 0.82494581 0.38963181 0.82367927 0.39626491 0.8173089 0.39445442
		 0.81571543 0.40049374 0.80799431 0.3986541 0.80926675 0.3929466 0.80116117 0.39777702
		 0.8063435 0.40440756 0.80226851 0.39214873 0.7954492 0.39201307 0.7960124 0.38595343;
	setAttr ".uvst[0].uvsp[1500:1749]" 0.80328953 0.38630742 0.79669422 0.37957466
		 0.79249257 0.37935328 0.79735345 0.37333268 0.80414248 0.38029164 0.80479652 0.37404084
		 0.81114709 0.38099051 0.81147128 0.37462187 0.8186236 0.37523508 0.81840682 0.36841297
		 0.82534158 0.36884081 0.82472754 0.36180604 0.83156341 0.36204064 0.83030212 0.35457397
		 0.83731699 0.35432786 0.83416468 0.34654939 0.82841229 0.34712595 0.82610607 0.3399837
		 0.82229584 0.34757829 0.82371724 0.35473168 0.81687891 0.35476768 0.81782085 0.36160016
		 0.81102431 0.36142594 0.81018734 0.35485715 0.81567371 0.34800112 0.80892372 0.34838182
		 0.81415379 0.34135354 0.82060885 0.34065866 0.81270969 0.33477211 0.80625403 0.33555031
		 0.80519795 0.32917637 0.80079305 0.32953185 0.79977274 0.32316947 0.79569477 0.3232078
		 0.79907644 0.31680608 0.80426806 0.32290798 0.80356359 0.31677055 0.80363309 0.31076729
		 0.8096922 0.31613165 0.80957311 0.31074572 0.81515169 0.31497228 0.81403482 0.30952734
		 0.82004875 0.31334096 0.82150668 0.31964844 0.82667255 0.3173964 0.82818031 0.32486033
		 0.83282626 0.32320142 0.83198923 0.31510711 0.82542378 0.3106187 0.83061457 0.30804658
		 0.8213954 0.30469823 0.82485032 0.30171895 0.81769055 0.29932082 0.82107079 0.29682326
		 0.81392986 0.2940138 0.81776792 0.29118764 0.81015593 0.28909522 0.81483644 0.28592312
		 0.80255091 0.28015941 0.80862427 0.27535307 0.7970798 0.2765314 0.79475439 0.28566492
		 0.7922017 0.28550941 0.79116827 0.2939502 0.79024386 0.28557467 0.79127276 0.27653432
		 0.79029417 0.27671117 0.79047322 0.26797843 0.78770781 0.26917392 0.78670228 0.26366532
		 0.78541356 0.26900196 0.78662914 0.27706623 0.78434378 0.27676535 0.78260112 0.28478479
		 0.78215098 0.27641553 0.78378332 0.26874971 0.78215122 0.26878524 0.78599632 0.26303405
		 0.78641969 0.2636131 0.78526354 0.2622847 0.77946621 0.268417 0.78004903 0.27626407
		 0.7767815 0.27583587 0.77646339 0.26813173 0.78170383 0.2598176 0.77711266 0.26052606
		 0.77876204 0.2544716 0.77052832 0.25452077 0.77137369 0.24778652 0.77722281 0.247217
		 0.77162009 0.24073142 0.77658647 0.24046028 0.77165246 0.23241305 0.7762711 0.23264641
		 0.77136862 0.22270572 0.77621531 0.22041869 0.76853788 0.21809238 0.76352477 0.22973776
		 0.76635462 0.23127192 0.75975817 0.23711354 0.76321369 0.23929316 0.7563771 0.24266636
		 0.75671744 0.23483694 0.75276393 0.23999518 0.75249666 0.24837232 0.74839574 0.2450453
		 0.74821907 0.25428379 0.75347453 0.25766742 0.74985647 0.2638585 0.7570523 0.26642239
		 0.7537567 0.27283263 0.76150763 0.27442253 0.76513714 0.26773369 0.76021439 0.26016927
		 0.76889777 0.26076674 0.76288372 0.25399536 0.75707763 0.25160879 0.76045072 0.24551755
		 0.76531315 0.24761587 0.76698923 0.24059659 0.76810861 0.2346347 0.77277601 0.26823515
		 0.76877815 0.27543545 0.77281845 0.27567935 0.77010095 0.28283596 0.7744388 0.28325069
		 0.7723465 0.29062736 0.77624488 0.29141259 0.77071947 0.29770529 0.76761413 0.28978145
		 0.76276869 0.2890507 0.76552433 0.28225803 0.7583214 0.28111821 0.75564659 0.28787613
		 0.7507053 0.27947187 0.74634701 0.27041072 0.74316472 0.27726591 0.7396102 0.26733732
		 0.74382043 0.26057589 0.73821247 0.25679332 0.73327613 0.26374137 0.72881979 0.27134585
		 0.73590088 0.27452677 0.72522175 0.27942431 0.73280877 0.28207791 0.7404325 0.28441918
		 0.73039287 0.28986621 0.72246003 0.28797734 0.72084904 0.29674101 0.72883272 0.29783428
		 0.73824954 0.29170847 0.73673427 0.29904759 0.72817206 0.30579758 0.72025973 0.30546606
		 0.72046083 0.31382501 0.72819126 0.31363273 0.7359311 0.30647111 0.72094834 0.32156479
		 0.74439538 0.30030257 0.75032383 0.30827105 0.74599236 0.29331017 0.7480914 0.28633976
		 0.74344617 0.25057203 0.77802682 0.28390825 0.78031713 0.28434324 0.78107101 0.29250813
		 0.78512162 0.28533757 0.78772712 0.29359639 0.78902107 0.28556663 0.78907025 0.29369384
		 0.78817636 0.30128121 0.79057354 0.30163455 0.79365355 0.29417038 0.79306203 0.30196857
		 0.79017717 0.30893648 0.78757179 0.30860025 0.78743893 0.31562781 0.78990537 0.3159858
		 0.78759468 0.32261693 0.7859931 0.32247484 0.78576308 0.32919067 0.78748667 0.32936406
		 0.78545564 0.33560461 0.7794686 0.34103584 0.78511155 0.34222281 0.78474712 0.34847176
		 0.78673202 0.34850597 0.78650922 0.35481024 0.7902146 0.34865099 0.79019129 0.34238809
		 0.79384059 0.34254408 0.79362547 0.3361187 0.79744673 0.34259385 0.79392332 0.34886873
		 0.79787427 0.34909439 0.80354631 0.3487854 0.80441731 0.35508633 0.80257237 0.34247565
		 0.80749017 0.34199059 0.80174488 0.33601224 0.79716176 0.33613586 0.79647249 0.32961941
		 0.79323047 0.32982451 0.79276609 0.32320786 0.78990108 0.32968724 0.79008567 0.33607805
		 0.78716964 0.33577448 0.78983855 0.32295007 0.78691137 0.34226912 0.79256785 0.31635785
		 0.79537928 0.31656313 0.79539949 0.30969971 0.79903835 0.31023037 0.80009192 0.30358481
		 0.80501938 0.30520838 0.80745476 0.30069125 0.81212682 0.30482173 0.81468594 0.30207348
		 0.81766552 0.30744958 0.80941397 0.3069852 0.81046724 0.29718447 0.8027336 0.2978906
		 0.8061766 0.29306817 0.79627013 0.29480648 0.79567719 0.30234134 0.79265863 0.30930936
		 0.79823965 0.28728735 0.79807568 0.35525084 0.80491841 0.36135978 0.79797983 0.36128891
		 0.80506873 0.36771846 0.81142586 0.36804104 0.79779392 0.36729729 0.79337305 0.36714923
		 0.79299986 0.37314862 0.78942823 0.36721349 0.78977501 0.36114907 0.78614509 0.36113811
		 0.78575343 0.36732292 0.78409392 0.36116028 0.78449702 0.35479248 0.78909731 0.37324589
		 0.78867602 0.37947607 0.79183757 0.38575518 0.79006326 0.35492647 0.79388279 0.35507202
		 0.79369664 0.36120468 0.78597116 0.31548858 0.76113176 0.22720635 0.76801896 0.21289337;
	setAttr ".uvst[0].uvsp[1750:1853]" 0.78346533 0.26127172 0.78992122 0.26364857
		 0.79185587 0.26729447 0.79175752 0.26174092 0.79743582 0.26537132 0.79412889 0.27586555
		 0.8025617 0.26725823 0.79694068 0.26083028 0.79342967 0.25542051 0.79112649 0.25580794
		 0.79092032 0.25132883 0.79074419 0.25133979 0.79019469 0.25573707 0.79061937 0.2513476
		 0.83456337 0.33062744 0.82946473 0.3319639 0.83631265 0.33774334 0.83102179 0.33917087
		 0.83986491 0.3451277 0.82461584 0.33296609 0.82317889 0.32618666 0.81757194 0.32734478
		 0.81629699 0.32100391 0.81045449 0.32209074 0.81150579 0.32836884 0.81897801 0.33389354
		 0.84463656 0.35339171 0.83971578 0.36252004 0.84823489 0.36230373 0.83926052 0.37019873
		 0.83198929 0.36940014 0.83181435 0.37667775 0.82562298 0.37592912 0.82562262 0.38293529
		 0.81862962 0.38190591 0.81827259 0.38831675 0.81044573 0.38706607 0.83886147 0.377882
		 0.8474232 0.37042522 0.84683394 0.3788358 0.81380272 0.4062773 0.84221381 0.40192461
		 0.8335582 0.40629297 0.84047747 0.40849298 0.8322283 0.41252065 0.82498652 0.415842
		 0.83007222 0.41828549 0.82337815 0.41971815 0.81705397 0.41892636 0.81611359 0.42429662
		 0.82563156 0.42343819 0.81606382 0.42947567 0.82803398 0.42769521 0.83517063 0.42152894
		 0.83846486 0.41501349 0.80658597 0.42845088 0.8079558 0.42281353 0.7993722 0.42713225
		 0.80102772 0.42141485 0.79357928 0.42583895 0.795057 0.42050326 0.7967177 0.41483927
		 0.79044116 0.41506857 0.79186475 0.40942949 0.78764057 0.40969592 0.78907967 0.40362644
		 0.78672242 0.40373945 0.7872166 0.39771664 0.78308612 0.39816165 0.78363931 0.39220047
		 0.78145492 0.39238489 0.78192925 0.38625085 0.77536768 0.38628209 0.7750147 0.39263105
		 0.7713607 0.38629425 0.77189219 0.37962985 0.76897269 0.37308693 0.77257413 0.37311077
		 0.76962686 0.36661321 0.76543975 0.36646539 0.76641756 0.35973984 0.76736277 0.3529346
		 0.77594918 0.37977922 0.77666432 0.37332249 0.78095269 0.3983891 0.78268236 0.40410376
		 0.78219104 0.41024399 0.78615636 0.41002196 0.78510606 0.4173888 0.78428161 0.42351985
		 0.78504622 0.4213953 0.78444797 0.42363304 0.78797966 0.42448592 0.78910089 0.42050618
		 0.78630775 0.41586459 0.76921952 0.33955824 0.77001941 0.33281761 0.76391578 0.33168256
		 0.77087706 0.32622564 0.7717889 0.31965792 0.7755481 0.31357229 0.77271473 0.31290591
		 0.77636743 0.30648977 0.72824764 0.39097333;
	setAttr ".cuvs" -type "string" "map1";
	setAttr ".dcc" -type "string" "Diffuse";
	setAttr ".covm[0]"  0 1 1;
	setAttr ".cdvm[0]"  0 1 1;
	setAttr -s 1854 ".vt";
	setAttr ".vt[0:165]"  9.75268173 78.71408081 17.59460449 11.94423199 77.21698761 16.75320435
		 11.60996246 79.1631546 17.052742004 9.44980431 81.04990387 17.67595673 7.9541626 78.26503754 17.66984558
		 9.91282654 76.014648438 17.31682587 8.58373356 73.50403595 17.27227783 12.19323826 75.18252563 16.46292877
		 14.043679237 76.55186462 15.61349487 13.53062725 78.48963928 15.70721054 15.1175766 78.6628952 14.46009064
		 13.29776096 79.75215149 15.79065704 11.33223915 81.28681183 17.16101837 12.98745251 81.69667053 15.83945465
		 11.095266342 83.45072937 17.15601349 9.21539688 83.37744141 17.64447784 10.91224289 85.64984894 17.14658356
		 12.721488 83.74300385 15.86563873 12.48240852 85.86660767 15.91861725 10.68554688 87.93028259 17.1787262
		 9.00036048889 85.72657776 17.60107422 8.79601288 88.091217041 17.5345459 10.37652016 90.4347229 17.21770477
		 11.77536964 90.56987762 16.38460541 11.29355621 93.36534882 16.63570404 12.76446533 91.22415924 14.98911285
		 13.42853546 88.70402527 14.74004364 14.66273689 89.11019897 13.31815338 13.98731709 86.36550903 14.56534576
		 12.20367622 88.097991943 16.10787964 14.40774822 84.19107056 14.47734833 16.11847496 84.56452179 13.1190567
		 16.4747448 82.45776367 12.98730469 17.69411469 84.90874481 11.51506805 17.063756943 87.21031952 11.73618317
		 19.064237595 85.3052597 9.75341797 19.57440376 82.97124481 9.71121216 21.28729248 83.49672699 8.6238327
		 21.65412331 80.9729538 8.71948242 23.066825867 81.42841339 7.10858917 23.34361649 78.89427948 7.16750336
		 24.33381462 79.87750244 4.30390167 23.70158577 82.11775208 4.724617 22.55477142 83.95998383 7.20675659
		 22.98241997 84.45979309 5.17295074 21.78189278 86.46646118 7.41848755 20.65003586 85.95606232 8.71570587
		 19.81035995 88.29133606 8.9806366 20.95715904 88.90428162 7.75861359 18.87743378 90.53829956 9.18112946
		 17.49596405 89.94294739 10.36057281 16.62814331 92.16658783 10.58055115 18.031053543 92.71380615 9.33164215
		 17.25580215 94.71012115 9.43373108 19.22739983 93.26215363 8.2226944 20.045665741 91.12744141 8.0074005127
		 20.4920063 91.4395752 6.34751129 21.33419418 89.21178436 6.015808105 22.18867111 86.84713745 5.61660004
		 19.68348885 93.56912231 6.59909821 18.5160656 95.17396545 8.37342834 18.95225143 95.38874054 6.78585052
		 17.82382011 96.90673065 8.50402832 18.31126022 97.088996887 6.9187851 17.24727058 98.61701965 8.53643799
		 16.50800705 96.48025513 9.50486755 15.82424164 94.28157043 10.70560455 15.13055325 96.15597534 10.8430481
		 15.90433598 98.26673126 9.59744263 14.58455753 98.044281006 10.95012665 15.46951962 100.11639404 9.61531067
		 16.76085091 100.39176941 8.51714325 17.77268791 98.77828979 7.008934021 17.32196999 100.48930359 7.071517944
		 16.37033272 102.28189087 8.4908371 16.93869019 102.32227325 7.10997772 15.97843647 104.33016205 8.46113586
		 14.81740284 104.15145874 9.51855469 14.67109585 106.45782471 9.59659576 13.63716602 106.3241272 10.81220245
		 13.54325485 108.72076416 11.03742218 12.40142632 106.39038086 11.60105896 12.40749454 104.13964844 11.41404724
		 11.40834999 104.30633545 12.45545959 11.41784286 102.099395752 12.50410461 10.79837227 102.39332581 13.84285736
		 10.80042458 104.55200958 13.70511627 11.34257889 106.51171875 12.50655365 10.62418365 106.70039368 13.61573029
		 11.37618065 108.91980743 12.71370697 12.45990753 108.79273987 11.90762329 12.56147003 111.37426758 12.18087006
		 13.49191475 111.29920959 11.27000427 14.29201984 111.27206421 10.14833832 14.44652843 108.88791656 9.87384796
		 15.056212425 111.27810669 8.56272125 15.29025364 108.99991608 8.52910614 15.61806202 106.56793976 8.45300293
		 15.97320461 108.85764313 7.023994446 16.29136658 106.49518585 7.092597961 16.60447121 104.3241272 7.11732483
		 15.64424038 111.28170013 6.9400177 11.42565536 111.46459198 13.025001526 10.38720703 109.029914856 13.58617401
		 10.16399002 111.4750061 13.82234192 9.38603401 109.099403381 14.41664886 9.65706444 106.9143219 14.55699921
		 9.71412659 104.84272003 14.70851135 8.28691769 104.98930359 15.33058929 8.19729424 102.99708557 15.46300507
		 6.41974068 103.046096802 15.9815979 6.56361961 100.75354004 16.37979126 4.46868134 102.98923492 16.53881836
		 6.55021 105.18370819 15.93654633 4.54827023 105.48538208 16.66858673 6.63538837 108.12003326 15.93560791
		 8.41579151 107.049873352 15.26655579 8.30695057 109.076179504 15.094085693 8.92682838 111.326828 14.56064606
		 7.75156116 110.99559021 15.21416473 7.18233204 109.45450592 15.63352203 6.41986036 110.67758179 15.88769531
		 4.51021624 110.30740356 16.70629883 4.70455408 100.44458771 16.52960205 7.013234615 98.29262543 16.9511261
		 8.69837189 98.69651794 16.75431061 7.61493015 95.88620758 17.29788971 5.12526798 97.66359711 16.67006683
		 5.56528282 95.34667969 16.86933899 6.025485039 93.058143616 17.067863464 8.099019051 93.30570984 17.42495728
		 9.2864666 96.083343506 17.256073 9.89692307 93.26898956 17.33235168 10.68058586 96.088874817 16.57590485
		 10.068216324 98.63352966 15.98519135 11.44426537 96.10105133 15.066047668 10.94393539 98.31455994 14.64846802
		 11.58159637 97.9447403 13.035850525 11.41072273 100.032249451 12.74703979 12.60826397 99.87142181 11.65248871
		 12.48178577 101.89891052 11.46996307 13.8868494 101.86956787 10.751297 14.14398289 99.92934418 10.84753418
		 15.09650898 102.038238525 9.55252075 13.75546932 104.028923035 10.72298431 12.96920776 97.88059998 11.88806915
		 13.59641838 95.89777374 12.014198303 12.1442585 95.83705139 13.2279892 12.84070015 93.80324554 13.33708954
		 12.070812225 93.82791138 15.13861847 13.71073532 91.47109985 13.36985779 14.37230301 93.96083069 12.091651917
		 15.27122116 91.80329895 12.106987 16.22531319 89.5588913 11.9613266 15.53356647 86.79479218 13.22389221
		 18.32118988 87.62359619 10.050765991 10.75351143 100.38630676 14.14671326 9.74600983 100.80237579 15.27953339
		 9.70989799 102.76683044 14.84954071 8.29287243 100.98368835 16.021202087 8.51516247 90.58119965 17.47640991
		 6.49261856 90.63652039 17.25031281 6.86528254 88.16819763 17.40840149 7.079442024 85.77823639 17.53538513
		 24.70550156 77.57302094 4.38502502 23.44740105 76.46767426 7.35931396;
	setAttr ".vt[166:331]" 21.68559837 78.17701721 9.19551086 21.86360168 75.2479248 9.20214081
		 19.84520531 77.69774628 10.61182404 19.89700317 80.60333252 9.95037842 18.21494102 78.1396637 11.80892181
		 17.76392174 75.54692078 12.95999527 16.74997902 76.34741974 13.7607193 16.718853 78.41914368 13.059951782
		 18.29276085 80.44707489 11.33257294 16.57507706 80.37866211 12.88661194 15.47022438 76.91882324 14.71077347
		 14.93909645 80.15761566 14.37602997 14.72198391 82.1400528 14.43363953 18.13384056 82.67059326 11.39148712
		 19.085479736 73.69369507 11.97431946 22.089597702 72.47202301 9.24005127 23.74138641 74.021598816 7.44752502
		 24.11530876 71.37379456 7.27842712 25.44164276 72.86205292 4.5383606 25.88440895 70.47999573 4.67220306
		 26.46483231 71.15990448 2.76294708 25.95726585 73.43913269 3.19835663 25.051544189 75.25996399 4.44734955
		 25.4323864 75.64569092 3.57215118 24.89917183 77.75713348 3.9254303 26.92266273 68.89507294 2.2337265
		 26.39225388 68.17359161 4.8638649 27.3174324 66.65081787 2.059753418 26.77700233 65.84857178 4.5992775
		 24.91568947 66.47364807 7.024532318 24.49199295 68.84992218 7.12617874 23.64380074 67.8418045 8.20728302
		 22.39698982 69.25343323 9.30872726 26.093463898 65.10464478 5.83650208 27.33504868 63.45041275 4.43024063
		 27.83733368 64.54286194 1.95219421 28.51800156 62.45652771 1.90844727 28.27131653 62.69423676 0.48181152
		 29.17411613 60.22848511 1.83454895 29.00019264221 60.11558914 0.062656403 30.25652504 57.3804245 0.17445374
		 28.3306179 61.8259697 3.099246979 27.77488708 64.68239594 1.029960632 27.35063744 66.71837616 1.63574219
		 20.74572563 71.32207489 10.69204712 7.2413168 83.37159729 17.62446594 7.43647242 80.94469452 17.68631744
		 -1.33102775 110.33843994 17.19841766 -2.76270247 110.47040558 16.87690735 -2.40182161 108.77763367 17.15031433
		 -1.053269386 105.49034119 17.3252182 -2.77126741 105.23056793 17.21994781 -0.95908594 102.74988556 17.27191925
		 -2.92473197 102.69961548 17.21131897 -1.17718852 100.39363861 17.17173004 -3.26343203 100.44296265 17.17779541
		 -1.50767422 98.1034317 17.14277649 -3.6942718 98.10523224 17.21421814 -5.40580845 100.38524628 16.99010468
		 -4.89863348 102.67082214 17.00048828125 -6.69695282 102.65948486 16.41486359 -6.10615587 105.20892334 16.50071716
		 -7.59846926 105.23858643 15.93601227 -8.31552792 102.72110748 15.78570557 -7.29569292 100.30934143 16.29070282
		 -8.96736622 100.4489212 15.61084747 -7.80040836 98.025863647 16.17159271 -5.94800901 98.03503418 17.037498474
		 -6.30181456 95.81306458 16.99990082 -4.018609524 95.8526535 17.22982788 -4.35034466 93.2040863 17.28816986
		 -6.59884644 93.25240326 17.0016784668 -4.70178843 90.2912674 17.36309814 -6.88419485 90.46073151 17.061149597
		 -5.11325741 87.34745026 17.43717194 -7.23756218 87.68928528 17.12958527 -7.66550875 85.0065917969 17.2221756
		 -9.5858078 85.46909332 16.33350372 -10.012990952 82.97776031 16.43903351 -11.79236507 83.43425751 15.53813171
		 -12.18757534 81.10253906 15.70729828 -14.02805233 81.56289673 15.2203598 -14.34544849 79.39283752 15.22637939
		 -16.051116943 79.70191956 14.73806 -16.3941803 77.82636261 14.52796936 -17.54027748 79.97429657 14.026069641
		 -17.064975739 82.061019897 14.30059814 -18.71705437 80.3691864 12.93087006 -19.26995468 78.37152863 12.62084961
		 -20.25371933 78.56906891 11.20159912 -20.83192635 76.3210144 11.26022339 -21.15761757 78.57159424 9.61743164
		 -20.3404541 81.0081787109 9.7223587 -21.35006523 81.040802002 8.0026473999 -22.14259529 78.38550568 8.042610168
		 -21.78363037 76.027061462 9.79298401 -22.73753738 75.64549255 8.32447052 -23.14700508 78.15324402 6.38126373
		 -22.3822403 80.93119049 6.27600098 -22.98922729 80.77497101 4.23123169 -22.25048828 83.43179321 4.20352936
		 -22.12912941 83.41188049 1.86976624 -22.97751617 80.74714661 1.76285553 -23.92794991 77.84906769 1.87628174
		 -23.7743988 78.038459778 -1.29574585 -24.83754921 74.87282562 -1.61746216 -24.80241585 74.65060425 2.024902344
		 -25.53372574 71.4335022 1.30770111 -25.92239761 71.30801392 -1.92194366 -26.28627396 68.56585693 1.016059875
		 -25.9382 68.48970032 3.55148315 -27.2468605 65.55204773 3.024303436 -27.50449944 65.54792023 0.62941742
		 -27.49183655 66.23401642 -2.37524414 -28.42621613 63.46985626 -2.69041443 -28.26443672 63.28910828 0.49452209
		 -29.61060715 60.095252991 -3.1212616 -26.6820755 68.77937317 -2.13253021 -25.28259087 68.40675354 5.89964676
		 -25.24494934 71.48960114 3.72441101 -24.57304573 71.85908508 5.91577911 -24.3946209 74.85070038 4.96304321
		 -23.68168831 75.22497559 6.72855377 -23.77661324 77.90972137 4.39458466 -23.86133385 72.28968811 7.40073395
		 -23.063041687 72.58230591 8.8502121 -23.96776962 68.95737457 8.2102356 -24.60778999 69.020935059 6.98007965
		 -23.26206398 68.98025513 9.5786972 -22.24189568 70.92085266 11.10393906 -22.11319733 73.53120422 10.28745651
		 -21.23661613 72.19775391 12.45714951 -21.12200928 74.15139008 11.67449188 -19.96912003 74.5919342 12.87405777
		 -20.16401863 72.98195648 13.50790787 -18.94002724 73.37478638 14.29966736 -18.60347366 74.69113922 13.81063461
		 -19.69146347 76.42779541 12.59021759 -18.28362465 76.3423996 13.63412476 -17.14728737 74.4575882 14.46086121
		 -17.63078117 73.16318512 14.8047142 -15.58806229 73.77223206 14.93938446 -15.064533234 75.50685883 14.95820999
		 -13.33811474 74.69415283 15.51147461 -12.89173031 76.7350769 15.67082214 -11.063644409 75.93123627 16.33983612
		 -10.70957947 78.22171021 16.45407867 -8.77364159 77.467453 17.13140869 -8.51304436 79.94444275 17.21035767
		 -6.38337135 79.24768829 17.43600464 -6.015547276 81.91065979 17.49001312 -3.94827056 81.53343964 17.49752045
		 -4.25529242 78.87211609 17.43995285 -6.61585426 76.83198547 17.34117889 -4.42787504 76.39506531 17.34540939
		 -6.93552208 74.28985596 17.20600128 -4.6949873 73.57576752 17.20811462 -7.51396418 71.67730713 17.00756073
		 -5.47368765 70.44120789 16.96144867 -8.27285004 68.89447784 16.63336182 -10.29784203 70.35102081 16.35399628
		 -10.86542988 68.31214905 15.94138718 -12.99874592 69.70487976 15.61839294 -12.22422886 71.6279068 15.86431122
		 -14.79509258 71.14357758 15.35325623 -13.9607172 72.79067993 15.3867836;
	setAttr ".vt[332:497]" -16.27668953 72.31843567 15.10700989 -11.55715656 73.72586823 16.13324738
		 -9.6438446 72.70156097 16.75753021 -9.11999321 75.086303711 16.97062683 -6.75914288 64.048248291 16.24837494
		 -3.55007648 84.094413757 17.51869965 -5.576684 84.52970886 17.48602295 -3.066400528 86.95124817 17.48736572
		 -2.59945607 89.9858551 17.39939117 -8.10498238 82.4543457 17.27371216 -10.3836689 80.55706787 16.49613953
		 -12.53511715 78.86073303 15.74401093 -14.68717289 77.3833313 15.10336685 -16.73139381 76.072463989 14.36816406
		 -17.94573975 78.10407257 13.74996185 -22.69276047 80.89482117 -0.95469666 -21.6534996 83.509758 -0.62159729
		 -20.71550941 85.99900818 -0.30879211 -21.38465309 85.90382385 2.051109314 -19.92610741 88.38288879 -0.026542664
		 -20.7500782 88.36115265 2.22177887 -19.29956818 90.6969223 0.22143555 -20.13442993 90.78865051 2.31446838
		 -18.8200779 93.024024963 0.43074799 -19.5604744 93.13591003 2.35914612 -20.26892853 90.92760468 4.26570892
		 -20.91008186 88.4519043 4.23960876 -19.47006416 90.8103714 6.019248962 -18.7564106 93.10811615 5.97496033
		 -17.58236122 92.79797363 7.91042328 -17.056936264 94.91203308 7.93505859 -16.010322571 94.71222687 10.088050842
		 -15.78419971 96.76282501 10.025436401 -15.1883297 96.78123474 12.0086898804 -14.9497261 98.87509155 11.82907867
		 -14.69412994 96.87158966 13.36844635 -15.13408089 94.62091064 13.42334747 -13.93264771 96.8369751 14.39753723
		 -13.40302086 99.096916199 14.23184967 -14.21772766 99.033973694 13.15869141 -12.89875221 101.18756104 14.080955505
		 -12.4021225 98.92449951 15.086509705 -12.91898918 96.62795258 15.096343994 -11.078569412 98.52224731 15.42664337
		 -10.51565552 100.80429077 15.43834686 -9.50695229 98.22975159 15.46988678 -9.90344429 95.87267303 15.34066772
		 -8.12400532 95.80230713 16.10565948 -8.42972088 93.32969666 16.054954529 -10.23114967 93.52753448 15.23557281
		 -10.56526184 90.92957306 15.1361618 -12.36967468 91.27036285 15.10900879 -12.74931908 88.73722839 15.070068359
		 -14.18613911 88.98273468 14.9879837 -13.20200253 86.26686096 15.11824799 -10.942276 88.36183167 15.18980408
		 -11.36623859 85.86608887 15.36728668 -13.65633297 83.86000824 15.17740631 -14.69033909 86.49462128 14.94833374
		 -15.26739788 84.095428467 14.98164368 -15.70145512 81.81197357 14.90473938 -16.50413132 84.37347412 14.44132996
		 -15.8852396 86.74528503 14.42575073 -17.42264938 84.73471069 13.43512726 -18.085428238 82.46083069 13.27745819
		 -18.73114014 82.90573883 11.83094025 -19.51568031 80.77041626 11.48673248 -19.49500847 83.27010345 9.8926239
		 -17.9496727 85.1033783 12.0024108887 -18.64119911 85.52580261 10.0065383911 -17.19836807 87.40539551 12.0066070557
		 -16.71060562 87.089859009 13.40834045 -16.10276222 89.53903198 13.37697601 -15.36708546 89.23687744 14.45094299
		 -14.86871147 91.84377289 14.45458984 -13.75970459 91.56435394 15.0071411133 -13.38282585 94.23813629 15.13591766
		 -12.024383545 93.90247345 15.23396301 -11.59307671 96.20677948 15.33983612 -14.46214867 94.5007019 14.5078125
		 -15.56321716 92.085723877 13.39060211 -15.91388512 92.26069641 12.0077972412 -16.50250816 89.80601501 11.98797607
		 -17.093206406 90.13842773 10.058502197 -17.84078979 87.82578278 10.054443359 -18.99589157 88.21027374 7.97425842
		 -19.72763443 85.87197876 8.0287323 -20.8907299 85.99206543 6.15398407 -21.61613464 83.53229523 6.21820831
		 -21.57835197 85.95098877 4.2230072 -20.17300606 88.42172241 6.075119019 -20.51628494 83.51935577 8.037788391
		 -18.27682686 90.51242828 7.92897034 -16.43801117 92.48356628 10.086708069 -15.48799324 94.62149811 12.046676636
		 -9.15236092 88.025161743 16.1712265 -8.77942657 90.649086 16.066940308 -9.88271713 102.95812225 15.49832916
		 -11.31529045 103.28948212 14.96317291 -10.6276226 105.43517303 14.88362885 -11.95790291 105.45175171 13.90996552
		 -11.42815781 107.49681091 13.71178436 -12.61205673 107.31243134 12.53029633 -12.26401329 109.21581268 12.2644043
		 -13.65418434 107.17675018 11.23318481 -13.036203384 105.30288696 12.69544983 -14.072376251 105.1486969 11.36930084
		 -13.42571449 103.20350647 12.81608582 -14.42658329 103.055000305 11.48374176 -13.80582428 101.11434174 12.95882416
		 -12.45996284 103.3383255 14.0063552856 -11.8579483 101.12077332 14.95770264 -14.69780159 100.96697998 11.61745453
		 -15.35437489 102.95510864 9.92277527 -15.043366432 105.069740295 9.92675781 -15.71605587 105.06072998 8.30006409
		 -14.54423046 107.12532043 9.85147858 -13.2259922 109.10118103 11.05809021 -14.0070466995 109.10020447 9.72777557
		 -15.19564342 107.15158081 8.33522034 -14.62048244 109.18060303 8.31056213 -15.63333607 107.23948669 6.73271179
		 -16.16723633 105.13422394 6.59066772 -15.9824667 107.37702942 5.10382843 -15.043103218 109.32489777 6.80950928
		 -15.32077312 109.49427795 5.24114227 -16.18379021 107.50287628 3.46153259 -16.59744453 105.27456665 4.89033508
		 -16.85535049 105.38430023 3.18354797 -17.077453613 103.21247864 4.62825775 -17.44109535 103.31169128 2.90529633
		 -17.53072739 101.21934509 4.41577148 -16.87428474 101.033836365 6.17475128 -18.0042247772 99.24365997 4.2976532
		 -17.90924454 101.27252197 2.69638824 -18.34610176 99.24024963 2.59694672 -18.47608948 97.25923157 4.25382996
		 -17.24844551 99.04649353 6.039962769 -17.67119789 97.088729858 5.97296906 -18.94363594 95.2985611 4.22524261
		 -18.69911385 97.22267914 2.52088165 -19.05664444 95.23589325 2.43982697 -18.24233818 97.15718079 0.72460175
		 -18.027990341 99.16085052 0.84319305 -17.77062416 101.21115112 0.98715973 -18.48220062 95.16834259 0.5963974
		 -19.58752632 93.27285004 4.25778961 -18.13216972 95.14632416 5.93466949 -16.70829201 96.87761688 7.96459198
		 -16.43117332 98.85775757 7.98364258 -15.61887074 98.78677368 9.94814301 -15.46558285 100.85077667 9.88381195
		 -16.16624641 100.89544678 8.04095459 -15.97926617 102.95128632 8.1700592 -16.54880714 103.053115845 6.37236786
		 -17.40511894 103.31354523 1.19102478 -16.9080677 105.45288086 1.46032715 -16.25398827 107.63685608 1.80828857
		 -15.51691341 109.77850342 2.18531036 -15.45548534 109.64884186 3.65972137 -11.10695648 109.46548462 13.35541534
		 -10.032682419 107.65344238 14.68131256 -9.80250072 109.82933044 14.28752899 -8.52679348 107.78712463 15.36058807
		 -9.12939548 105.30950928 15.46668243 -6.98714209 107.88884735 15.92525482;
	setAttr ".vt[498:663]" -8.27786541 110.2474823 15.079711914 -6.53385162 110.5604248 15.78684998
		 -5.48757172 107.86561584 16.46298981 -4.50053072 105.17647552 16.99152374 -3.81241035 108.39151001 16.90013885
		 -4.68190956 110.43460083 16.38048553 -2.19523406 92.98535156 17.28330231 -1.83936596 95.7275238 17.18595123
		 -15.56736755 64.90844727 -9.036437988 -19.22680283 66.37280273 -8.10548401 -16.27339363 67.14625549 -8.53232574
		 -13.24529457 66.074806213 -10.32320404 -12.29698372 63.88483429 -10.89144897 -14.23468876 62.64806747 -9.82416916
		 -16.50671005 61.26599503 -9.42388535 -14.60160637 58.98685837 -10.34700394 -18.30707741 59.63616943 -9.90245819
		 -16.058683395 57.45268631 -10.54697037 -12.4643631 56.98907089 -11.3964119 -11.2400341 58.59859085 -11.68392563
		 -10.057673454 55.8997345 -12.46337128 -13.519701 55.33220673 -11.37058258 -10.79038334 53.85905838 -12.39132309
		 -8.1510725 53.1962738 -13.39050293 -7.73689795 55.57999039 -13.38801193 -5.61036634 53.14312363 -14.2942543
		 -5.68331146 55.70175552 -14.14172745 -3.45711303 53.55594254 -14.94208908 -3.82015848 56.13169098 -14.72129059
		 -5.7800355 58.26632309 -14.04340744 -7.50949907 57.9697876 -13.41438293 -7.60508299 60.50871658 -13.34005356
		 -9.15732861 60.097328186 -12.65013885 -9.67698288 62.47724915 -12.39107132 -10.39672565 60.014240265 -12.011013031
		 -9.36551094 57.93036652 -12.59651184 -12.85422611 60.45766449 -10.68740845 -11.20897007 61.66666031 -11.54458237
		 -10.45419502 64.77075958 -11.97647095 -8.016759872 63.043567657 -13.12882614 -8.58108521 65.422966 -12.81053925
		 -6.28112078 63.51311493 -13.67597198 -5.92323446 60.95152283 -13.93386078 -4.36209536 61.34490585 -14.30080795
		 -4.08990097 58.76224136 -14.55587387 -2.44792247 59.3408165 -14.92071152 -2.73158145 61.88672256 -14.57787704
		 -0.81339669 59.91321564 -15.058647156 -0.43024963 57.34750366 -15.2861557 1.2092191 57.89271927 -15.18189621
		 1.72886145 55.38933563 -15.37142944 3.324435 55.84270096 -15.025997162 2.83593678 58.33968353 -14.85019684
		 0.82023323 60.41833878 -14.97516251 2.46092987 60.82818222 -14.66152573 4.51310062 58.73749924 -14.38189316
		 5.028542519 56.24209595 -14.56578827 6.88305044 56.69701767 -14.11601639 6.30809355 59.19106674 -13.90781784
		 4.12485981 61.1889534 -14.16340256 5.79688263 61.74298096 -13.72975159 8.16426373 59.86632538 -13.50071716
		 8.81947613 57.39530182 -13.76746368 10.82025337 58.18506622 -13.40618896 10.10469055 60.59625244 -13.078990936
		 7.73237896 62.29303741 -13.23924637 9.7269268 62.9740448 -12.76261902 12.0010433197 61.39671326 -12.65516663
		 12.67982101 59.0573349 -13.024002075 14.21007156 59.81124878 -12.54333496 13.8462162 62.13195038 -12.18769073
		 11.79521942 63.71586227 -12.28557205 14.076664925 64.24321747 -11.84052277 15.64560699 62.4025383 -11.7103157
		 16.160326 64.37627411 -11.4175415 17.22743225 62.35773087 -10.72189713 17.78575134 64.2974472 -10.55606079
		 18.58771706 62.36994553 -9.28500748 18.35804939 60.99133682 -9.29893875 19.61535072 62.23485565 -7.42650223
		 18.89064217 64.19731903 -9.11283112 19.5970993 63.95652771 -7.12031555 20.73130035 61.80513 -5.45507813
		 19.5405159 60.72086716 -7.65758896 20.79574585 60.17332458 -5.91082764 22.27754593 61.2420311 -3.67520523
		 22.16210747 63.11106873 -3.21574402 24.12942314 62.78432465 -1.81971741 23.98534203 64.84937286 -1.47954559
		 25.93118858 64.74544525 -0.2273941 25.6553688 66.82939148 0.19831848 27.35063744 66.71837616 1.63574219
		 26.92266273 68.89507294 2.2337265 25.36121559 68.97229004 0.66140747 23.86590576 66.9862442 -1.18351746
		 23.68367386 69.15432739 -0.82944489 24.96170998 71.16325378 1.15213776 23.37515068 71.32001495 -0.3967514
		 22.040786743 69.26378632 -2.3542099 21.79127121 71.43027496 -1.95165253 21.42957306 73.58592987 -1.52379608
		 20.073633194 73.7409668 -3.26156616 19.76369095 75.9076767 -2.91498566 18.72360039 76.099967957 -4.8555069
		 18.52683067 78.22788239 -4.60023499 17.6420002 78.35929871 -6.47498322 17.4539814 80.43947601 -6.24628448
		 16.26368713 80.49062347 -7.78175354 15.99974442 82.58087158 -7.57142639 14.54762363 80.30284882 -8.71955109
		 14.25922394 82.35056305 -8.54011536 13.94181156 84.43482971 -8.39017487 11.98705387 84.11551666 -9.12742615
		 11.73013687 86.29776001 -9.081573486 13.62103558 86.61235046 -8.24736023 11.47262001 88.61535645 -9.041549683
		 13.30908966 88.89107513 -8.11630249 11.22596455 91.01750946 -9.021903992 13.018137932 91.17321777 -8.021575928
		 12.74051476 93.47696686 -7.94793701 14.56211472 93.60966492 -6.88804626 14.2700367 95.59429169 -6.81048584
		 15.92873001 93.65798187 -5.39686584 15.59733963 95.68474579 -5.37332153 13.98575974 97.59473419 -6.66227722
		 12.5082283 95.49499512 -7.86455536 12.31855965 97.50406647 -7.7177887 10.80637932 95.56880188 -8.91329193
		 10.99620628 93.45178986 -8.9909668 9.38869286 93.56227875 -10.048233032 9.58238697 91.017745972 -10.086128235
		 9.75123787 88.49617767 -10.097885132 8.032773018 88.59236908 -10.9445343 8.10820198 86.12480164 -10.95799255
		 6.22821808 86.3039856 -11.3476944 6.19616413 88.76544952 -11.17445374 7.91519403 91.15572357 -10.88101196
		 6.11923075 91.29469299 -11.017868042 4.33926344 88.94185638 -10.96747589 4.30497265 86.52294159 -11.15068054
		 2.47757077 86.70698547 -10.89469147 2.54375052 89.13552856 -10.77391815 4.32434034 91.42329407 -10.88109589
		 2.52389312 91.53488159 -10.79640198 0.77194947 91.54483032 -10.73083496 0.89783514 94.030006409 -10.91077423
		 -0.82061893 93.90751648 -10.77510071 -0.75385487 96.30741882 -10.91400146 -2.37694025 96.085891724 -10.69332886
		 -2.42475748 98.48767853 -10.72344208 -0.74982858 98.69178009 -11.0078430176 0.976942 96.41059875 -11.087364197
		 0.96083063 98.76569366 -11.15527344 2.69562435 98.7618103 -11.018882751 0.9877128 101.077033997 -10.89376068
		 -0.77504891 100.99039459 -10.84965515 -0.78219986 103.0094833374 -10.28233337 0.99791074 103.11797333 -10.32423401
		 2.70825624 101.076377869 -10.70999146 2.7563262 103.21286011 -10.33769989 4.4089427 101.035522461 -10.55480194
		 4.3322072 98.65312958 -10.84200287 2.65479851 96.36289215 -11.04624939 4.2676363 96.22227478 -10.93047333
		 2.57935071 93.94971466 -10.88393402 4.284935 93.87656403 -10.89539337;
	setAttr ".vt[664:829]" 5.89817381 96.10044861 -10.84964752 5.87549686 98.47335052 -10.70978546
		 7.43215132 98.27870178 -10.43025208 7.51896477 100.63169098 -10.093254089 9.028224945 100.19482422 -9.47024536
		 9.189147 102.42692566 -8.93276215 10.69728661 101.89008331 -8.14733124 10.90147781 104.1476059 -7.4678421
		 12.22767448 103.89305115 -6.58389282 12.4032917 106.21006012 -5.67986298 13.62554932 105.9513855 -4.62527466
		 13.79155922 108.22588348 -3.59201813 14.68656731 105.6389389 -3.31798553 14.63570404 103.55950165 -4.065917969
		 15.59905243 103.30426788 -2.46109772 15.60918236 105.35966492 -1.8660965 16.19649696 103.10199738 -0.69766998
		 16.21937561 105.15593719 -0.27625275 15.66015244 107.71705627 -1.043266296 14.82113457 107.97428131 -2.38682556
		 14.53830528 110.20069122 -1.25299835 15.3360157 109.97572327 0.085029602 14.0060768127 111.95069885 -0.42234802
		 12.96092892 111.98318481 -1.70985413 13.49512672 110.30348206 -2.49913788 12.27846432 110.33093262 -3.59957123
		 12.51892471 108.4206543 -4.59242249 11.091919899 108.50376892 -5.45645142 11.074193954 106.40900421 -6.49054718
		 9.56509686 106.59765625 -7.14936066 9.40301228 104.55126953 -8.13826752 7.74971867 104.79020691 -8.44785309
		 7.63448715 102.80947876 -9.40692139 6.040627956 103.034202576 -9.7975769 6.0067615509 100.89476013 -10.40984344
		 4.45552778 103.19509888 -10.15537262 6.12926531 104.96389771 -8.89561462 4.51988173 105.14186859 -9.51377106
		 2.77808833 105.13333893 -9.81694031 2.75924039 106.81732941 -9.053390503 4.51345158 106.84473419 -8.67926788
		 6.17840719 106.72387695 -7.98423004 6.16912031 108.40273285 -7.212677 7.87086248 106.67438507 -7.53975677
		 7.8893218 108.46177673 -6.72289276 7.73014116 110.1368866 -5.96192169 9.35330296 110.24297333 -5.31890869
		 8.96199322 111.85055542 -4.56636047 10.46097469 111.94706726 -3.7748642 10.88249683 110.31135559 -4.53446198
		 9.55749226 108.51692963 -6.19125366 11.78683949 111.9866333 -2.82045746 7.3956027 111.72653961 -5.24985504
		 6.037408829 110.031761169 -6.51615906 5.75302219 111.59011841 -5.84908295 4.32539511 109.95389557 -7.051246643
		 4.45833588 108.41203308 -7.83433533 2.69970632 108.31471252 -8.18065643 0.91325611 108.092788696 -8.12794495
		 0.81317478 109.68972778 -7.48984528 2.57348895 109.83473969 -7.3835907 2.3909657 111.34041595 -6.70018005
		 4.096392155 111.45748138 -6.35526276 0.68804199 111.25819397 -6.91785431 -0.95031017 109.59375 -7.54462433
		 -1.028213978 111.22432709 -7.012916565 -2.70258117 109.54862213 -7.52640533 -2.68494821 107.93373108 -8.18091583
		 -4.4122839 109.45397949 -7.26806641 -4.46015501 111.14221191 -6.71134949 -6.097391605 111.01991272 -6.22364807
		 -6.037540436 109.25523376 -6.69757843 -4.42984009 107.83005524 -7.95721436 -6.03688097 107.56829834 -7.27839661
		 -4.41084433 106.22383881 -8.61677551 -2.66339302 106.36779022 -8.87755585 -2.62687588 104.73468781 -9.63046265
		 -0.84289569 106.39344025 -8.76794434 -0.88645977 107.95795441 -8.10360718 0.97343463 106.56887817 -8.89231873
		 0.99082881 104.93919373 -9.67332458 -0.80949157 104.77722168 -9.54608917 -2.60010862 102.9262085 -10.28740692
		 -4.40086079 104.57837677 -9.38889313 -4.36639786 102.74825287 -10.08656311 -2.50033617 100.82050323 -10.61299896
		 -4.18909454 100.55953979 -10.41461945 -4.083935738 98.1625824 -10.51865387 -5.79412699 100.1878891 -10.17990112
		 -5.98082066 102.42055511 -9.62623596 -7.51012182 102.033241272 -9.19906616 -7.54206371 103.8863678 -8.18400574
		 -9.11632252 103.51924896 -7.74781036 -9.23760128 105.34653473 -6.80392456 -7.57602787 105.61423492 -7.29708862
		 -5.99478436 104.2229538 -8.71631622 -6.0069541931 105.90448761 -7.88961029 -7.60654116 107.31230927 -6.60083008
		 -9.23100758 107.10215759 -6.032348633 -9.14518547 108.87472534 -5.38110352 -7.61794138 109.053962708 -6.048095703
		 -9.035762787 110.63703918 -4.80788422 -10.30000019 110.4379425 -3.96914673 -10.58048725 108.74571228 -4.70306396
		 -11.44708347 110.26890564 -3.08996582 -11.83423328 108.61071014 -3.90104675 -10.76282024 106.88697052 -5.45515442
		 -10.77782917 104.94920349 -6.26625824 -12.10008335 106.61569977 -4.71661377 -12.080644608 104.34776306 -5.53256989
		 -10.60265636 102.92890167 -7.19860077 -11.83361053 102.12039948 -6.21623993 -10.39618301 100.8907547 -8.054374695
		 -8.97838497 101.57601929 -8.76674652 -8.87315845 99.29494476 -9.40592194 -10.29132462 98.72944641 -8.47680664
		 -8.93437099 96.87377167 -9.62598419 -7.35538435 97.33209229 -10.11534882 -7.48037767 94.89150238 -10.24907684
		 -5.75040007 95.33332062 -10.39225006 -5.7306385 97.75834656 -10.34731293 -4.058692932 95.74284363 -10.52444458
		 -2.356457 93.67827606 -10.64131927 -4.049215317 93.31712341 -10.54298401 -2.32442355 91.13033295 -10.62976074
		 -0.68020219 91.42384338 -10.66889191 -0.59035444 88.94606018 -10.6105423 0.74242115 89.063316345 -10.63497925
		 0.68853146 86.64334106 -10.71013641 2.40713167 84.33195496 -11.10326385 0.88438392 83.89547729 -10.83161163
		 2.56139112 81.79737854 -11.25289154 4.25607491 84.2052002 -11.35568237 6.20680094 83.99040222 -11.44987488
		 4.32717943 81.81708527 -11.45857239 6.18965387 81.68193817 -11.49197388 8.16727161 83.80974579 -10.96234131
		 9.90852928 86.09866333 -10.07623291 10.081280708 83.88337708 -10.062759399 12.25772285 82.032752991 -9.22528839
		 10.24847794 81.78633118 -10.067138672 8.2496748 81.64438629 -10.93959045 8.36941719 79.58444977 -10.94107056
		 10.43511391 79.71459961 -10.11141205 12.52240944 79.99133301 -9.3416748 12.77760696 77.96115112 -9.4981308
		 14.80222607 78.2616272 -8.91418457 15.048383713 76.21353912 -9.14871216 16.47814751 78.41229248 -7.98162079
		 16.70853615 76.32704163 -8.23344421 17.83870697 76.24790955 -6.72163391 18.040719986 74.13723755 -6.99873352
		 16.91872215 74.26773071 -8.50493622 18.23125648 72.066947937 -7.32570648 19.13280487 71.78504181 -5.513237
		 19.27803612 69.7167511 -5.94860077 20.54473305 69.43410492 -4.056030273 20.62360573 67.37168884 -4.41485596
		 22.16690254 67.14772797 -2.68740082 20.57124901 65.38993073 -4.66963196 19.45456314 65.77661133 -6.73045349
		 20.57991791 63.53676987 -5.0028419495 22.1668911 65.092956543 -2.93626404 18.86191368 66.18267059 -8.68975067
		 18.60963058 68.11291504 -8.14981079 17.6143074 68.36740875 -9.62461853;
	setAttr ".vt[830:995]" 17.3631916 70.30150604 -9.20970917 16.086019516 68.27062988 -10.53091431
		 15.7952919 70.23286438 -10.13276672 17.13607597 72.2637558 -8.83385468 18.42961693 70.063049316 -7.7118988
		 15.53120327 72.21215057 -9.78981018 15.28377724 74.19816589 -9.44800568 13.2738266 73.93708801 -9.9799881
		 13.023101807 75.9433136 -9.70470428 10.82621956 75.65827942 -10.34387207 10.6236248 77.67825317 -10.18545532
		 8.67174339 75.46562195 -11.10488129 8.51183033 77.53578186 -10.98331451 6.5654664 75.32897949 -11.75159454
		 6.42211246 77.44263458 -11.60446167 6.286654 79.54970551 -11.52498627 4.39533186 77.40034485 -11.87752533
		 4.54539967 75.24700165 -12.14717865 2.62279677 75.13519287 -12.20639038 2.76568913 77.48930359 -11.79061127
		 4.26652813 79.56328583 -11.6859436 2.61787033 79.62908936 -11.51010132 0.90858752 81.70236206 -11.12533569
		 0.96285278 79.52656555 -11.44151306 -0.66187561 81.52607727 -11.27412415 -0.68775868 83.73077393 -10.89446259
		 -0.47292474 86.53386688 -10.72802734 -2.17997289 86.20813751 -10.94735718 -2.26496172 88.62026215 -10.6896286
		 -4.049913406 88.1965332 -10.93000793 -4.051690102 90.71243286 -10.64944458 -5.92943954 90.23445892 -10.8155365
		 -5.81614351 92.85856628 -10.51272583 -7.67437601 92.35184479 -10.46450806 -9.14701939 94.47137451 -9.69868469
		 -9.4299345 91.85334015 -9.70309448 -7.88316107 89.65505981 -10.72723389 -9.69291306 89.049926758 -9.81453705
		 -11.029294014 91.492836 -8.58425903 -10.63074875 94.14403534 -8.47089386 -12.25731087 93.9173584 -7.50301361
		 -11.81795502 96.10294342 -7.21645355 -10.38542747 96.44829559 -8.52585602 -11.59210777 98.12534332 -7.054428101
		 -13.15172386 97.76316071 -5.933815 -12.98665619 99.57444763 -5.47601318 -11.64860153 100.079689026 -6.7381134
		 -12.97664261 101.56652069 -5.054153442 -14.15492058 101.44145203 -4.014877319 -13.041074753 103.84575653 -4.55188751
		 -13.98924828 103.5827713 -3.52771759 -14.98280907 101.3221283 -2.74533844 -15.1509037 99.29901123 -3.22964478
		 -14.34687042 99.44966125 -4.49769592 -15.29297447 97.3182373 -3.68730164 -16.11821556 97.17746735 -2.26356506
		 -16.56305313 95.26914215 -2.66249847 -15.49580002 95.33087158 -4.080764771 -17.12076569 93.27379608 -3.057189941
		 -15.86254406 93.20314026 -4.40440369 -15.014598846 93.40219116 -5.75883484 -16.55335617 90.77085114 -4.66977692
		 -15.4439249 90.67176819 -5.8616333 -14.37083721 90.93431854 -7.12905121 -14.88133335 88.015823364 -7.12724304
		 -13.37666893 88.32761383 -8.24895477 -13.88569069 85.5080719 -8.38453674 -11.87885666 85.88970947 -9.16048431
		 -11.4826088 88.63651276 -8.88508606 -9.84740829 86.33759308 -9.97939301 -9.92869473 83.90997314 -10.16436005
		 -7.91814089 84.53916931 -11.22770691 -7.9833107 87.028533936 -10.99500275 -5.95711231 85.26004791 -11.64360809
		 -5.85212135 82.91838837 -12.0097045898 -3.91937375 83.48203278 -11.7697525 -3.94554901 80.99636841 -12.16013336
		 -2.25396752 81.30448151 -11.66681671 -2.22652221 79.065078735 -12.067741394 -0.61698651 79.33139038 -11.64205933
		 -0.55273163 77.13098145 -11.99885559 1.12294412 77.35765839 -11.78057861 1.19073391 75.18933105 -12.16189575
		 2.77708983 72.93312836 -12.58472443 0.98666543 72.73132324 -12.60497284 -0.42954633 74.91725159 -12.34589386
		 -0.26969594 72.7256012 -12.71157837 1.12541461 70.46849823 -13.038208008 2.91813278 70.69836426 -13.017982483
		 3.18010879 68.43386078 -13.38404083 4.872756 70.85256195 -12.74478912 4.69228411 73.061653137 -12.4324646
		 6.72633934 73.20050049 -11.9556427 6.91501808 71.062194824 -12.19582367 9.050969124 71.3155365 -11.5421524
		 9.24628639 69.24423218 -11.83599854 11.52228355 69.58765411 -11.21138 11.28780079 71.60838318 -10.87574005
		 13.82608604 69.94460297 -10.66506958 13.53981686 71.93939972 -10.30495453 11.047300339 73.63508606 -10.57701874
		 8.85589409 73.39705658 -11.29360962 14.086438179 67.97666168 -11.04044342 16.27961159 66.32705688 -10.95225525
		 14.19565105 66.10305786 -11.43096924 11.72562408 67.61962128 -11.57280731 11.81546497 65.68335724 -11.92931366
		 9.41911888 67.20159149 -12.15882874 7.098248005 68.91551208 -12.45537567 7.28604174 66.77482605 -12.71888733
		 9.56170273 65.14260864 -12.46484375 7.48030567 64.59143066 -12.97776794 5.28496504 66.4047699 -13.25046539
		 5.086591721 68.64654541 -13.006111145 3.39294434 66.12770081 -13.69709015 5.50312185 64.119133 -13.49423981
		 3.62974215 63.7626915 -13.99631882 1.92615664 65.57818604 -13.8784256 1.35287547 68.16762543 -13.48534393
		 0.062119637 67.51208496 -13.53988647 -0.12824841 69.76563263 -13.10748291 -1.3671627 69.75814056 -13.40340424
		 -1.58001983 72.053138733 -13.077575684 -1.7527312 74.32791138 -12.78177643 -3.6458087 73.92668915 -13.13819122
		 -3.72379041 76.22355652 -12.9029007 -5.78014994 75.81768036 -12.83539581 -5.75840664 78.12931824 -12.59789276
		 -7.89116049 77.63572693 -11.92853546 -7.86975718 79.9006424 -11.64399719 -10.11976624 79.36584473 -10.83087158
		 -10.038414001 81.61604309 -10.46710205 -12.4123764 81.081222534 -9.76698303 -12.20270824 83.39928436 -9.45779419
		 -14.29972458 82.92240906 -8.4463501 -15.36745167 85.212677 -6.92939758 -15.89503479 82.45955658 -6.86225128
		 -14.49225426 80.46356964 -8.55482483 -16.18018532 79.92263794 -6.98458099 -14.53635883 77.97281647 -8.72992706
		 -12.49343109 78.74801636 -10.10451508 -12.51498222 76.36875153 -10.42920685 -10.16803741 77.061172485 -11.2143631
		 -10.13142967 74.73154449 -11.59939575 -7.88685656 75.33489227 -12.26995087 -7.77678394 72.99899292 -12.5965271
		 -5.69094801 73.49082184 -13.071311951 -5.47204971 71.16329956 -13.29456329 -3.46985364 71.63314819 -13.36677551
		 -3.22664237 69.3123703 -13.60518646 -1.59212303 67.11273193 -13.71079254 -2.95687532 66.95896149 -13.91607666
		 -1.36209011 64.8091507 -14.14781952 0.2668575 65.22718048 -14.022628784 0.51426542 62.86878586 -14.53778458
		 2.16816592 63.25152206 -14.3315239 -1.10611069 62.40940857 -14.63594055 -3.00031709671 64.32920837 -14.17690277
		 -4.70504236 63.82561874 -13.97579575 -4.82907867 66.43152618 -13.76667786 -6.70031261 65.95040894 -13.39547729
		 -7.13541746 68.28349304 -13.12885284 -9.15441513 67.73625946 -12.49635315 -9.61969471 70.031578064 -12.23471832
		 -11.7930069 69.25206757 -11.24866486 -12.20653629 71.58360291 -10.98046112;
	setAttr ".vt[996:1161]" -14.38240719 70.5968399 -9.61148834 -14.54823399 73.027130127 -9.27213287
		 -16.73603821 72.034751892 -7.76686096 -16.58454704 74.63831329 -7.40371704 -14.56375885 75.49665833 -8.95824432
		 -12.428936 73.96530914 -10.7057724 -16.35945892 77.24556732 -7.16191101 -18.60666466 77.088600159 -6.5128479
		 -18.22108078 79.8019104 -6.21911621 -20.58734322 77.49531555 -6.10930634 -18.99679756 74.33644867 -6.86094666
		 -21.1502552 74.50978088 -6.51927948 -19.31071663 71.42424011 -7.25100708 -16.65822601 69.49594879 -8.16972351
		 -19.37319756 68.78723907 -7.63824463 -13.92469597 68.25737762 -9.92747498 -21.66532707 71.52346039 -6.98989105
		 -22.053024292 68.70526886 -7.42324066 -23.45532036 71.80791473 -5.88928986 -22.78609276 74.89039612 -5.41968536
		 -24.72826576 71.79615021 -4.1046524 -25.51616096 68.92747498 -4.36553192 -25.92239761 71.30801392 -1.92194366
		 -24.83754921 74.87282562 -1.61746216 -23.85782433 74.95970154 -3.70799255 -22.969244 78.0048446655 -3.241745
		 -22.015270233 77.85499573 -4.91657257 -21.22024918 80.66033173 -4.48045349 -19.94447708 80.28359985 -5.66262054
		 -19.24002838 83.10670471 -5.27731323 -17.65689659 82.54830933 -5.9295578 -16.88340759 85.28310394 -5.74630737
		 -18.41791344 85.86593628 -4.97351074 -17.44987488 88.33771515 -4.8234024 -16.090433121 87.93541718 -5.77935791
		 -17.78966141 91.066078186 -3.39163971 -18.58065414 88.74478149 -3.60297394 -19.3519516 88.6438446 -2.0051727295
		 -20.17560005 86.13540649 -2.28360748 -19.48361397 86.16251373 -3.82585144 -21.092679977 83.51626587 -2.52307129
		 -21.6534996 83.509758 -0.62159729 -22.69276047 80.89482117 -0.95469666 -22.037218094 80.81270599 -2.83698273
		 -20.36688232 83.42066956 -4.1188736 -23.7743988 78.038459778 -1.29574585 -20.71550941 85.99900818 -0.30879211
		 -19.92610741 88.38288879 -0.026542664 -19.29956818 90.6969223 0.22143555 -18.66341972 90.95583344 -1.69067383
		 -18.8200779 93.024024963 0.43074799 -18.11296272 93.19863892 -1.39707184 -17.62486839 95.22751617 -1.10683441
		 -18.48220062 95.16834259 0.5963974 -17.20765114 97.15750122 -0.79798889 -15.75916672 99.12207031 -1.80521393
		 -16.84479141 99.091331482 -0.47576904 -18.24233818 97.15718079 0.72460175 -18.027990341 99.16085052 0.84319305
		 -17.77062416 101.21115112 0.98715973 -16.47805786 101.074028015 -0.10665894 -17.40511894 103.31354523 1.19102478
		 -16.16151619 103.14089203 0.26722717 -15.32093048 103.18612671 -0.88948822 -15.21882439 105.30062103 -0.45231628
		 -14.7448864 105.51673126 -1.66903687 -14.48563194 107.68732452 -0.98223877 -13.79467392 107.974617 -1.94195557
		 -13.38149738 110.035316467 -1.14521027 -12.4762907 110.14640045 -2.15838623 -12.89148426 108.37091064 -2.94462585
		 -13.93477249 105.84786987 -2.85099792 -13.093105316 106.26018524 -3.82913208 -14.034897804 109.9695816 -0.30071259
		 -15.00014400482 107.56095886 0.034957886 -14.60002232 109.91654205 0.53375244 -15.55179501 107.51715088 0.98577881
		 -15.89407158 105.259552 0.61595917 -16.25398827 107.63685608 1.80828857 -15.099448204 109.85189056 1.38837433
		 -15.51691341 109.77850342 2.18531036 -16.9080677 105.45288086 1.46032715 -14.87971306 103.39093781 -2.24845886
		 -15.50286484 101.12957001 -1.35074615 -26.6820755 68.77937317 -2.13253021 -27.49183655 66.23401642 -2.37524414
		 -26.29034233 66.31255341 -4.41280365 -26.93384743 63.69297028 -4.51078033 -24.62812233 66.030006409 -6.39157867
		 -24.89846802 63.76448822 -6.38150787 -22.19430161 63.83281708 -7.91051483 -22.51304054 61.99868774 -8.15917206
		 -20.4463501 61.2509346 -9.1562767 -18.81712341 63.59992218 -8.6938324 -22.22765732 66.056015015 -7.77310181
		 -24.09860611 68.82972717 -6.28707886 -25.0081577301 61.87841034 -6.58860779 -27.25507164 61.16944885 -4.95514679
		 -28.42621613 63.46985626 -2.69041443 -29.61060715 60.095252991 -3.1212616 -9.96925831 72.38214111 -11.96435547
		 -11.18688774 67.019920349 -11.56746674 -7.51500463 70.62501526 -12.87334442 -5.160285 68.80466461 -13.52193451
		 -7.86244106 82.19358826 -11.41846466 -5.74798679 80.44526672 -12.32816315 -3.73560023 78.56419373 -12.61870575
		 -2.1792202 76.81251526 -12.41338348 -2.2755928 83.52825928 -11.23001099 -4.0065073967 85.80200195 -11.32775879
		 -5.99241257 87.70819092 -11.23123169 -12.80853367 91.25108337 -7.89816284 -13.89062691 93.72113037 -6.81069183
		 -13.47472954 95.85899353 -6.39898682 -14.72957611 95.59866333 -5.43701935 -14.54789162 97.57933807 -5.029968262
		 17.85417366 66.38220215 -10.12043762 19.37418747 67.71486664 -6.34843445 20.34183121 71.55989075 -3.644104
		 18.92905045 73.92678833 -5.15673065 -7.3517971 99.75948334 -9.85198212 -7.62814903 110.84207916 -5.57118225
		 -2.75417852 111.19993591 -6.96147919 14.86430454 111.8764801 1.13262939 15.86168098 109.58779144 1.59367371
		 16.18638802 107.39501953 0.44701385 16.20485115 106.92812347 2.076797485 15.97766781 109.071128845 3.062965393
		 15.9354372 106.45835114 3.86761475 15.88091373 108.79680634 4.43198395 15.98642826 106.30648041 5.57979584
		 15.89275837 108.72149658 5.78463745 15.74756145 111.52935028 5.0037612915 15.67092991 111.65392303 3.93034363
		 15.72380543 111.39967346 6.0044555664 15.97320461 108.85764313 7.023994446 16.29136658 106.49518585 7.092597961
		 15.64424038 111.28170013 6.9400177 16.60447121 104.3241272 7.11732483 16.090597153 104.23164368 5.37070465
		 16.93869019 102.32227325 7.10997772 16.24957466 102.30150604 5.20580292 15.95175171 102.63278961 3.19670105
		 16.18615341 100.75661469 2.88793182 16.39876366 101.050010681 0.94834137 16.56762123 99.16149139 0.72106171
		 16.22953033 101.20114136 -1.019729614 16.31428528 99.34152985 -1.28504181 15.66234016 101.39672089 -2.91309357
		 15.79291344 99.51557922 -3.25282288 14.78186417 101.6140213 -4.64138031 15.011489868 99.66225433 -5.038589478
		 13.57917595 101.64874268 -6.10359955 13.75699234 99.61382294 -6.45206451 15.26565552 97.68275452 -5.2603302
		 16.035663605 97.61805725 -3.47097015 16.39576912 95.69908142 -3.57717896 16.78552055 93.71324158 -3.5847702
		 17.37613869 93.73440552 -1.64576721 17.87353516 91.48184204 -1.66455078 17.13640404 91.40774536 -3.5615387
		 16.23759651 91.37142181 -5.40058136 17.43114853 89.095825195 -3.60385895 16.50193596 89.10825348 -5.46704102
		 14.84459209 91.34373474 -6.95659637 15.12893772 89.13140869 -7.070075989;
	setAttr ".vt[1162:1327]" 15.41635036 86.89824677 -7.20405579 16.76381111 86.86087036 -5.61535645
		 17.019708633 84.65830994 -5.80141449 15.72631931 84.70810699 -7.38487244 17.24140739 82.52471924 -6.016494751
		 18.14766312 82.41161346 -4.12958527 18.34089279 80.30196381 -4.35777283 19.26414299 80.1541214 -2.40843964
		 19.041521072 82.32288361 -2.20207214 17.9342823 84.59775543 -3.91296387 18.79947472 84.56043243 -2.0042953491
		 17.69275856 86.83470154 -3.72674561 18.53530121 86.86953735 -1.82197571 18.23282242 89.19706726 -1.69602203
		 19.30009842 86.83088684 0.07408905 18.90258598 89.17434692 0.23296356 18.38851929 91.46635437 0.3321228
		 17.77368927 93.64523315 0.39563751 18.10079002 93.49510193 2.48777008 17.41874313 95.32498169 2.56945038
		 17.23946571 95.51703644 0.45860291 16.86879349 97.091362 2.63664246 18.036413193 95.27602386 4.69455719
		 18.77484322 93.46448517 4.56167603 19.68348885 93.56912231 6.59909821 20.4920063 91.4395752 6.34751129
		 19.54910278 91.32133484 4.38334656 21.33419418 89.21178436 6.015808105 20.31953049 89.066963196 4.13784027
		 18.84411049 91.36013794 2.36828613 19.4701252 89.082290649 2.21270752 21.037197113 86.72428131 3.84724426
		 22.18867111 86.84713745 5.61660004 22.98241997 84.45979309 5.17295074 21.71080208 84.39073181 3.50647736
		 23.70158577 82.11775208 4.724617 22.3069973 82.10044861 3.16492462 20.56205368 84.3988266 1.76646423
		 20.055290222 86.7443924 2.0018386841 19.64768982 84.48629761 -0.10662842 21.0089969635 82.1086731 1.52394104
		 19.96543694 82.19942474 -0.30084991 21.46188164 79.91389465 1.2420578 20.26485634 80.0076599121 -0.51274872
		 21.93763924 77.77705383 0.90792084 20.6128521 77.87194824 -0.78297424 19.50319481 78.03490448 -2.64135742
		 21.022089005 75.72661591 -1.12680054 22.4587574 75.64160919 0.50436401 22.94868088 73.47833252 0.066795349
		 24.47846985 73.40904236 1.61803436 26.46483231 71.15990448 2.76294708 25.95726585 73.43913269 3.19835663
		 23.95555687 75.61486053 2.044792175 25.4323864 75.64569092 3.57215118 23.41431236 77.75901794 2.43789673
		 24.89917183 77.75713348 3.9254303 22.8603611 79.89051819 2.81507874 24.33381462 79.87750244 4.30390167
		 18.95225143 95.38874054 6.78585052 17.39830971 96.98783875 4.79601288 18.31126022 97.088996887 6.9187851
		 16.897995 98.69961548 4.881073 16.49267578 98.89894867 2.7011795 16.8492794 97.33441162 0.554039
		 16.53610802 100.43318176 5.0069580078 17.77268791 98.77828979 7.008934021 17.32196999 100.48930359 7.071517944
		 16.91985512 95.64821625 -1.5959549 16.54863548 97.49917603 -1.48075867 12.19991875 99.55469513 -7.50284576
		 10.65426254 97.65155792 -8.76644135 10.6065197 99.7565155 -8.52016449 9.037223816 97.98174286 -9.77292633
		 9.18878555 95.78292084 -9.95740509 7.54640198 95.9761734 -10.61316681 7.73473835 93.69759369 -10.74815369
		 6.0078787804 93.78752136 -10.92153931 12.17463303 101.6395874 -7.18430328 13.48941612 103.75318146 -5.47544098
		 16.24523926 102.95116425 1.197258 15.89914322 104.516716 3.47614288 16.21627998 104.92458344 1.48715973
		 15.36840343 111.78694153 2.47164917 27.77488708 64.68239594 1.029960632 26.25160599 62.64764404 -0.63850403
		 28.27131653 62.69423676 0.48181152 26.57532883 60.42218781 -0.97899628 24.27674103 60.76452637 -2.21245956
		 24.34685135 58.77233124 -2.60044479 27.042490005 57.3660202 -1.26034546 29.00019264221 60.11558914 0.062656403
		 30.25652504 57.3804245 0.17445374 22.32840538 59.44902039 -4.17947388 17.072811127 60.88627243 -10.72689438
		 15.58929443 60.42123413 -11.86390305 0.13728714 54.82670593 -15.50896454 -2.083550215 56.733078 -15.11849213
		 -1.57874799 54.16731262 -15.37217712 4.35694265 105.65898895 16.88599396 4.19922686 107.5609436 17.66061401
		 3.8326962 107.16564941 16.96221161 2.77295876 107.56311035 16.99046326 3.54157853 105.64770508 16.38893127
		 2.478894 105.61196899 16.40453339 3.22561669 103.6605072 15.8560257 4.15673685 103.58952332 16.2032547
		 3.97921562 101.66297913 15.80168152 3.044750929 101.67696381 15.54529572 3.96513343 99.7051239 15.60797882
		 4.79340649 101.60869598 16.48259735 4.76797152 99.67700958 16.24542236 3.99997473 97.73551941 15.61224365
		 3.045101166 97.72286224 15.70628357 3.064242363 95.7749939 15.76437378 2.13805532 97.68264008 16.33033752
		 2.13035798 99.63853455 16.10558319 0.60625142 99.46078491 16.88471985 0.7654826 101.41732025 16.71681213
		 -1.26741302 101.4621582 17.2733078 -0.88887042 103.46882629 17.3965683 0.97742456 103.43656158 16.66753387
		 2.11199021 101.57261658 15.95690155 2.16316867 103.5872879 16.034759521 3.011200428 99.69022369 15.52307892
		 1.24567235 105.4318924 16.89266205 1.46606588 107.35336304 17.37162018 -0.24380974 107.14926147 17.99688721
		 -0.26431182 108.61650085 18.37605286 1.56949151 108.65927887 17.97668457 3.074734688 108.52429199 17.64468384
		 3.37801027 109.57260895 17.87480164 4.52693892 107.61039734 18.064170837 4.69669485 109.9128952 17.71126556
		 3.079591513 112.1639328 18.08455658 1.55066538 111.73773193 18.093231201 1.47164631 109.93264008 18.059761047
		 -0.49363986 110.193573 18.47396851 0.23082075 112.70013428 18.1754303 2.58765483 114.32470703 17.70535278
		 5.22756672 112.49160004 17.62247467 5.01883173 114.75304413 17.16916656 6.82132816 113.10761261 16.86078644
		 7.204741 111.69258118 16.36576843 6.9339242 109.87728119 16.24333191 5.326931 107.7571106 18.079269409
		 7.015656948 107.9427948 16.71089935 9.04079628 109.82247925 15.18868256 9.095814705 107.94818878 15.50739288
		 9.19040203 106.029800415 15.72593689 10.13827038 107.81900024 14.90070343 10.14974117 109.74649048 14.80078125
		 9.70536518 109.61407471 14.23776245 9.58014202 111.58440399 14.5144577 8.59305763 111.28147125 15.0098648071
		 8.53703022 113.01448822 15.48299408 9.41461849 113.32286072 15.026054382 9.94765186 111.74217224 14.82675934
		 9.72521305 113.49580383 15.19766235 9.29280376 114.73814392 15.35514832 8.50636482 114.66348267 15.80838013
		 9.52770901 114.81905365 15.27823639 8.83955765 113.47907257 15.7975235 8.97089291 111.76531982 15.31771088
		 8.6693573 114.78474426 15.79910278 6.57519531 114.76655579 16.65986633;
	setAttr ".vt[1328:1493]" 7.092619419 114.56686401 16.5511322 7.031317234 112.60327148 16.3181839
		 6.58743811 114.53554535 16.79004669 6.51174545 112.52655792 16.60045624 6.89008236 110.78944397 16.018211365
		 8.64243793 109.43570709 14.83682251 6.91500235 108.98134613 15.94203186 8.73974133 107.58493805 14.98252869
		 9.71732044 107.72290802 14.26770782 9.66575336 105.91220093 13.94389343 10.092305183 105.95482635 14.84295654
		 10.072594643 104.046112061 14.67055511 9.14640331 104.13423157 15.54314423 9.11425114 102.10690308 15.37257385
		 10.10938358 102.043251038 14.59514618 9.36708546 100.13604736 15.65722656 7.53798628 99.93185425 17.10205841
		 7.78509283 97.92286682 17.25188446 5.55349016 99.68486023 17.0027923584 5.4813242 101.61125183 17.17893219
		 7.27580833 101.84657288 16.86619568 5.40652132 103.53813934 17.51726532 4.81625032 103.5309906 16.89338684
		 4.80337095 105.54694366 17.52003479 5.4939003 105.54989624 17.87952423 7.041990757 105.84984589 16.85270691
		 7.055839062 103.77811432 16.73061371 5.62198162 97.70973206 16.95771027 4.85364342 97.72357178 16.13970184
		 5.78252316 95.72046661 16.80015564 8.036581993 95.87104797 17.24599457 8.16198921 93.6920166 17.24040985
		 5.84732246 93.55328369 16.73845673 8.28483677 91.38103485 17.27269745 10.43085957 91.5191803 16.42354584
		 8.51059341 88.98225403 17.31423187 6.25850773 88.85011292 16.80256653 6.52854347 86.38658905 17.014945984
		 5.32848883 86.28781128 16.19111633 5.4867959 83.75582886 16.37458801 3.95651245 86.24962616 15.78533173
		 4.041737556 88.79725647 15.616745 2.43956947 86.49264526 15.97601318 2.10210109 83.9529953 16.12302399
		 0.64456457 86.82978821 16.49971008 1.18233919 89.21721649 16.45043945 -1.10407293 89.49562073 16.84725952
		 -0.57981515 91.63607788 16.96717072 -3.22703671 92.0184021 17.02709198 -2.80367422 93.98635101 17.089027405
		 -0.13227217 93.70803833 17.065155029 1.62012339 91.4972229 16.45965576 1.89532924 93.69113159 16.45847321
		 0.21702431 95.68553925 17.11558533 -2.40384698 95.83579254 17.14446259 -2.023115873 97.60069275 17.18416595
		 0.48898816 97.55434418 17.031303406 2.065351725 95.73177338 16.44412231 -1.65545237 99.42506409 17.21524811
		 3.0066041946 93.69023132 15.75345612 2.94266129 91.3968277 15.75185394 4.074555874 93.65350342 15.54409027
		 4.072266102 95.77527618 15.59342957 5.015895367 95.75117493 16.011489868 5.03574419 93.59623718 15.9450531
		 4.07452774 91.29682922 15.52476501 5.11134052 91.25927734 15.89917755 5.98331976 91.24846649 16.73739624
		 5.21774817 88.79325104 15.99676514 2.74284101 88.97480011 15.81518555 -3.68327069 89.9216156 16.97129822
		 -1.74717844 87.17738342 16.74478912 -4.20254898 87.59315491 16.93584442 -2.38855815 84.65356445 16.63944244
		 0.032475509 84.29875946 16.44329071 -0.55000579 81.62905884 16.26141357 1.77970016 81.33856964 16.13376617
		 1.57807422 78.704422 16.069019318 3.90768576 81.12201691 15.97174835 3.90337563 83.69431305 15.93083191
		 5.73091078 81.16514587 16.47250366 6.80139589 83.82349396 17.157547 7.1201086 81.20333099 17.19088745
		 8.86042118 83.9078598 17.42803955 9.05038166 81.33181763 17.37633133 7.45769978 78.57470703 17.15618134
		 5.97746658 78.57113647 16.52890778 6.21768951 75.9740448 16.53678513 4.071007252 76.00440979 16.014396667
		 4.30879021 73.40447998 15.94498444 6.50826502 73.3764801 16.49995041 7.75275755 75.9484024 17.051475525
		 8.05659771 73.36755371 16.8913002 9.50469494 76.061294556 17.11081696 9.27940845 78.72040558 17.28115845
		 10.78666019 76.22731018 16.66882706 10.9599123 73.55947876 16.47833633 11.22276974 73.63648224 15.6882782
		 11.44390774 70.90734863 15.47724533 10.71243 73.64930725 15.098770142 10.56913662 76.29109955 15.22976303
		 9.86577702 73.70053101 15.13523865 10.1219492 70.89750671 14.97525024 8.65316296 73.6337738 15.80069351
		 9.72648335 76.37780762 15.35430527 8.56498909 76.49305725 16.14290619 9.54555416 79.027450562 15.4278717
		 10.43196583 78.91898346 15.30407333 10.31142712 81.41908264 15.19632721 10.84330082 81.44514465 15.88056183
		 10.83263874 83.90572357 15.79807281 10.31073284 83.86817932 15.0070724487 9.3416605 81.5614624 15.29218292
		 9.32128811 84.073951721 15.06237793 10.41190815 86.37998962 14.85441589 9.41000462 86.60709381 14.95749664
		 10.49895763 88.87454987 14.66562653 10.91196728 86.40937805 15.70578003 10.93314648 88.97203064 15.55974579
		 10.88561535 91.4919281 15.37581635 10.54166698 91.42037201 14.38091278 10.43969822 93.83000183 14.21952057
		 9.55100155 91.52642059 14.7125473 9.4152441 93.84669495 14.60949707 10.30915928 95.99446106 14.087150574
		 10.83609676 93.88851166 15.26067352 10.71731281 96.10089111 15.14621735 10.13946056 97.95710754 13.90317535
		 9.27628803 95.97097778 14.56092834 9.053139687 97.91819763 14.4389267 8.1065836 97.87931061 16.15438843
		 7.81418276 99.69474792 16.078666687 7.40732193 99.6026535 16.5626297 7.10105848 101.50608826 16.47323608
		 7.56893444 101.60620117 16.0020446777 6.84992599 103.43383026 16.37039185 5.67784691 103.16238403 16.78636932
		 5.54133511 104.9637146 16.80834198 5.47357893 104.94557953 15.77223969 5.46630573 106.70172119 16.070068359
		 6.65773058 106.60517883 15.44049072 6.51004887 108.36668396 15.62503052 8.2758894 108.17059326 14.66415405
		 8.043438911 109.87788391 14.77140045 9.70286465 109.98900604 13.82006073 9.54923534 111.61431885 14.21089172
		 11.72640705 110.34064484 12.92147064 11.47802067 111.90885925 13.30409241 13.56840038 110.83413696 11.93867493
		 13.83386707 109.26728058 11.74395752 14.86545658 109.64068604 10.39699554 15.16748905 107.94129181 10.37512207
		 14.12734509 107.56406403 11.56704712 15.55449009 106.13397217 10.25398254 16.50666428 106.53773499 8.5619812
		 16.93166542 104.56757355 8.49732208 18.0030078888 104.92711639 6.54438782 18.54370689 102.68073273 6.53700256
		 17.33854675 102.47412872 8.51650238 15.93625736 104.20214081 10.12229919 16.22089195 102.2226181 10.16046143
		 14.61153126 103.88928986 11.059524536 14.42442989 105.76306152 11.27759552 12.5535059 105.34385681 11.82648468
		 12.32642651 107.073196411 12.17453766 10.20803547 106.63715363 13.25965118;
	setAttr ".vt[1494:1659]" 10.31009769 104.99584961 12.86697388 8.43871593 106.47478485 14.42225647
		 9.97790432 108.31301117 13.58106232 8.49089336 104.83470154 14.051429749 6.62013102 104.92082214 15.041023254
		 6.59534597 103.10849762 14.83234406 8.61378384 103.12173462 13.78608704 6.7247324 101.19517517 14.71861267
		 5.81764221 101.13121796 15.70748138 7.02191782 99.33612823 14.70227814 8.78877068 101.35662842 13.62604523
		 8.99801731 99.52098846 13.53777313 10.70340061 101.52514648 12.64245605 10.83946514 99.67716217 12.68225098
		 12.84980488 99.85443115 11.9406662 12.86467838 97.89466095 12.062667847 14.81869602 98.03578186 11.43515778
		 14.80285931 96.047576904 11.762146 16.63971329 96.12237549 10.92931366 16.53453255 93.88830566 11.44565582
		 18.1071434 93.73159027 10.091888428 17.58976364 91.2266922 10.87937164 16.2721386 91.45445251 11.96123505
		 15.88781834 88.97280884 12.39025879 14.57602215 91.54685974 12.60202789 14.73437023 93.9099884 12.19425964
		 12.77579021 93.83727264 12.68614197 12.8468523 95.93920898 12.33386993 10.93162251 95.83701324 12.94677734
		 10.85688877 93.77965546 13.17539215 12.66279316 91.57219696 13.028259277 10.70610714 91.58145905 13.45282745
		 12.50541592 89.23765564 13.43603516 14.35907459 89.12385559 12.96014404 12.37414455 86.832901 13.78160858
		 10.48401165 86.97024536 14.19676208 10.40204906 84.54151917 14.22146606 9.099572182 84.63162994 14.60784149
		 9.15593815 82.25348663 15.00046539307 7.94372463 82.21134186 15.30260468 9.27890491 79.8188858 15.18427277
		 10.46707058 82.21309662 14.57627869 10.59191227 79.91762543 14.84445953 10.88971615 77.65503693 14.80562592
		 12.38623905 79.87784576 14.35562134 12.62906933 77.89997101 14.42660904 13.98305416 79.64949799 13.859375
		 13.95464993 77.64389801 14.0042915344 15.37671947 79.22589874 13.24155426 15.46480846 81.53723145 13.04825592
		 16.86865044 80.87491608 12.25728607 16.93315506 83.58473206 12.063720703 18.099014282 83.094802856 11.25000763
		 18.24900436 80.22756958 11.35242462 16.85766983 78.43350983 12.38857269 18.24625587 77.70543671 11.52367401
		 16.13466644 76.22096252 12.92823029 17.16457176 75.32502747 12.39368057 15.45633411 74.21575928 13.32875443
		 16.50868797 73.53913879 12.9158287 14.74405766 72.21273804 13.56932831 16.0039825439 71.51741791 13.25975037
		 14.014603615 70.313797 13.65166473 15.58106709 69.61945343 13.4422226 12.60414791 66.72631073 13.59635544
		 14.74906254 65.67263031 13.43148804 11.41077328 65.01713562 13.6281395 9.85426426 67.95091248 14.10300064
		 9.15179348 67.66611481 14.35601807 8.11000443 70.69207764 14.98861694 8.94688892 67.5822525 14.92337799
		 9.81876278 64.44721985 14.060474396 9.92626095 64.52651978 14.3236351 10.81824398 61.60543823 13.92215729
		 11.4353857 62.27703857 14.12237549 12.19026852 60.52410126 14.24172211 11.99116802 62.42803574 14.44504166
		 10.91522312 65.041030884 14.34262848 11.57191753 65.16318512 14.46830368 11.23154354 68.08000946 14.70396042
		 11.86699963 65.21263123 15.048484802 12.081784248 62.44446945 14.92040634 11.83540249 62.53786469 15.35121918
		 12.25322437 60.34716034 14.44359589 12.23683643 60.52689362 14.30628967 12.20852757 60.11992264 14.67322922
		 11.09509182 62.54948425 15.73159027 11.58481121 65.27722931 15.63739777 10.63825512 65.29586792 16.015678406
		 10.19628811 62.61536407 15.95705032 11.35874081 59.43112946 15.39278412 10.045390129 59.93266296 15.77182007
		 10.28919888 57.73754501 15.66129684 7.77034807 58.25090027 15.51643372 7.70351315 55.88174057 15.49048233
		 9.47309589 55.33401489 15.69401932 7.41648817 53.44926453 15.49147797 8.96204185 53.050762177 15.59500504
		 6.99171019 50.60620117 15.38156128 8.48560905 50.39867401 15.43193054 6.32416821 47.70217514 15.26042938
		 7.77101946 46.78968048 15.23812866 5.063093185 46.50441742 15.16103745 4.056990147 50.20703888 15.32927704
		 5.14670134 50.54968643 15.34618759 3.1524024 52.95432663 15.54506302 4.52490854 53.48065186 15.48142242
		 2.28254628 55.064720154 15.66311646 1.87469089 52.37170029 15.55922318 0.75583732 54.38031769 15.79458618
		 1.24484777 57.26263428 15.77823639 -0.49653098 56.38287354 15.98664093 0.083338134 59.55829239 15.89878464
		 2.21468043 60.39202881 15.6178093 1.30775523 62.75584412 15.69319916 4.016445637 63.19528961 15.44891739
		 3.24827552 65.63404083 15.5361557 5.92752361 65.70357513 15.64942932 6.74081802 63.15027237 15.60454941
		 4.73651409 60.83197021 15.37998199 7.56322193 60.50741577 15.59000397 5.28694105 58.53481293 15.33909607
		 3.12018991 58.080055237 15.51329041 3.9369688 55.78059769 15.47789383 5.73504257 56.19342804 15.39440918
		 5.89086056 53.6910553 15.47879028 5.93710852 51.58534241 15.39601135 9.08566761 62.86401367 15.94549561
		 8.19897842 65.60968018 16.060066223 9.43166256 65.45738983 16.1842804 8.91099358 68.1256485 16.46308136
		 10.26462841 68.03352356 16.32398605 9.9437418 70.76972961 16.6529808 11.12785244 70.84520721 16.20664215
		 9.69825649 73.41215515 16.90143204 8.43158627 70.7353363 16.71096039 6.94237089 70.7720871 16.37168121
		 7.50051022 68.19815063 16.22700119 5.23723984 68.25067902 15.73048401 4.69832563 70.81159973 15.83373642
		 2.57086444 68.15525055 15.60105133 0.45660076 65.24282074 15.68712234 -0.25229809 67.833992 15.67967224
		 -2.13383913 64.5772934 15.9981575 -1.08672452 61.99105072 15.96658325 -3.29906368 61.030891418 16.27142715
		 -4.47632647 63.71632385 16.43004608 -5.39315128 66.61040497 16.6333847 -2.94274306 67.29728699 16.058010101
		 -5.97691774 69.64002991 16.84666061 -3.4984839 70.13116455 16.13389969 -0.77161431 70.53317261 15.71291351
		 -3.79957414 73.046432495 16.23178864 -6.28315592 72.81997681 17.010662079 -6.2461834 76.04927063 17.071601868
		 -3.80525303 76.022415161 16.31950378 -1.075028896 73.28709412 15.8050499 -1.13672066 76.061180115 15.92625427
		 -3.51626468 78.99062347 16.39846802 -5.9222846 79.24699402 17.048374176 -5.3819046 82.29335022 16.98484802
		 -3.0075528622 81.89191437 16.51984406 -0.94619006 78.85943604 16.062850952 -4.7750659 85.082015991 16.94015503
		 1.55765915 76.052307129 15.96063232 3.94486976 78.56372833 16.02129364;
	setAttr ".vt[1660:1825]" 1.71701717 73.39837646 15.81841278 2.054095984 70.75719452 15.67526245
		 -1.89735651 58.58104706 16.14008331 11.33082485 68.080757141 15.9151001 11.64594555 68.10678101 15.25314713
		 10.95904255 70.9033432 14.91982651 10.44855976 68.022346497 14.7197113 8.89958668 70.72773743 15.46791458
		 9.30395222 67.69863892 14.95650482 8.47079659 70.6554184 15.52233124 8.22559261 73.61847687 15.94549561
		 7.56177187 73.68524933 15.60160065 8.73754597 70.93888092 14.52137375 8.053854942 73.8854599 14.97060394
		 7.41145754 76.59792328 16.064178467 8.14787006 76.49111938 16.3280983 8.024271965 79.27610016 16.59450531
		 7.28693151 79.39810181 16.47542953 7.89407253 82.033042908 16.68595123 8.1826067 81.96806335 16.28007507
		 8.28078175 84.55747986 16.2951355 7.97881651 84.62957764 16.74172974 8.49958324 86.97492218 16.32862854
		 9.51832867 89.050445557 14.84001923 8.64307117 89.43021393 16.30298615 8.59945011 91.68190002 16.2503891
		 8.21178436 91.64527893 16.71836853 8.086720467 93.80802917 16.74555969 7.15332174 91.61745453 16.88317871
		 7.30370045 89.44790649 16.76976013 7.067786694 89.54212952 15.75783539 7.087818623 87.20761108 15.71872711
		 7.80289698 89.54392242 14.98505402 6.96408129 91.7388916 15.79910278 7.67966795 91.82123566 14.8374939
		 9.17726612 91.68803406 13.97846985 9.25146198 93.81984711 13.81092834 9.20787144 89.48646545 14.400383
		 10.59956264 89.35101318 13.95345306 9.15257168 87.093238831 14.50351715 7.79883289 87.16642761 14.8890152
		 7.8149128 84.66566467 15.022407532 7.098373413 84.82183838 15.76930237 7.18341446 82.24557495 15.82704163
		 7.23170853 84.80446625 16.75683594 7.30671883 87.18776703 16.73388672 8.19071484 87.034736633 16.75679779
		 7.20253944 82.17889404 16.69114685 8.27697468 89.42268372 16.70214844 7.38710213 79.5476532 15.70554352
		 8.18682957 79.64780426 15.38011169 8.44883823 76.97510529 15.10298538 9.53752995 77.28242493 14.98353958
		 10.14584064 74.81080627 14.61446762 11.54916286 75.64743042 14.52622986 12.49591732 74.14260864 14.22590256
		 13.64180851 75.86392212 14.072402954 14.49656582 75.019584656 13.74650574 15.038573265 77.045700073 13.52187729
		 12.76408291 76.51444244 14.38536453 13.57095242 73.084564209 13.91361237 11.24882412 72.86906433 14.23543549
		 12.57770634 71.38986969 13.92231369 9.48620129 71.35133362 14.33021545 8.84498692 74.13970947 14.7670517
		 7.64052486 76.76886749 15.35377502 10.71250248 68.80892944 13.93372345 7.57636881 93.88391113 14.77340698
		 9.27873516 95.79167175 13.70786285 7.49001169 95.7728653 14.79262543 9.19373989 97.65973663 13.59341431
		 10.90952206 97.7638092 12.76394653 7.30705595 97.54904938 14.73135376 6.5063448 97.49609375 15.80400848
		 6.16510916 99.27148438 15.75524902 6.68004465 97.57096863 16.95387268 6.8827877 95.75123596 17.013084412
		 7.96936035 95.87271118 16.747612 7.73268414 97.77380371 16.66015625 8.34921741 95.93936157 16.24247742
		 8.4678154 93.86375427 16.25302887 6.29534245 99.36297607 16.94373322 5.92031717 101.24625397 16.89777374
		 5.59926367 103.078964233 15.68603516 7.0058298111 93.74412537 16.97637177 6.81486177 93.81282806 15.82203674
		 6.72613096 95.7444458 15.8427887 8.36648846 79.23619843 16.28404236 3.026724577 49.55699158 15.25539398
		 4.55093956 45.030288696 14.94338226 11.87129116 59.84776688 15.12650681 11.42654324 60.23429871 13.85720825
		 10.90072536 61.43645859 13.48863602 11.38728428 59.64517975 13.25267792 12.64635754 61.33739853 13.21683121
		 10.65191364 64.5114212 13.72859955 13.86010075 62.45962906 13.25099564 12.91171169 59.71276855 13.07352066
		 12.15884304 57.58425522 12.95240402 11.45984936 57.61254501 13.11802292 11.53423023 56.076084137 12.92612076
		 11.48645687 56.072052002 12.95186996 11.49760532 57.5318222 13.39031982 11.45258045 56.069187164 12.97011948
		 18.19970894 85.73641205 10.93958282 16.96929359 86.14904785 11.85914612 18.2837944 88.20617676 10.51709747
		 17.090288162 88.70733643 11.55329895 18.77024078 90.67831421 9.67655945 15.74194431 86.44313812 12.63742065
		 15.62173557 83.95200348 12.82678986 14.050068855 84.22109985 13.43582916 13.97848415 81.85708618 13.60368347
		 12.26957417 82.052597046 14.037956238 12.2694006 84.40343475 13.82079315 14.17337132 86.6593399 13.25330353
		 19.55150795 93.30281067 8.50332642 18.41184807 96.15859222 9.29634857 20.03968811 95.94743347 7.3944931
		 18.016288757 98.27731323 8.96501923 16.58394432 98.18122101 10.57590485 16.42214966 100.21565247 10.34794617
		 14.82508945 100.044868469 11.27249908 14.74441624 102.0057144165 11.026229858 12.76383114 101.7504425 11.69520569
		 12.66763973 103.58586121 11.58848572 10.50450611 103.28678131 12.63399506 17.70296478 100.40245056 8.67329407
		 19.42754364 98.1509552 7.023635864 18.98770905 100.46250153 6.68631744 12.02663517 108.73740387 12.53601837
		 17.52283859 106.90438843 6.62724304 16.14022636 108.35064697 8.6170578 17.12278938 108.7596817 6.7506485
		 15.85072327 110.11543274 8.6712265 14.747859 111.23681641 10.37740326 15.54194927 111.79375458 9.01260376
		 14.53213406 112.37273407 10.65613556 13.33900356 112.28186035 12.12845612 13.18664455 113.83287048 12.12594604
		 14.93187237 113.37360382 9.97837067 13.21798801 115.31954193 11.96952057 15.33451557 114.52069092 9.23922729
		 16.31928635 112.56477356 7.60936737 16.76242256 110.63227081 6.98607635 11.20151043 115.1909256 13.89459991
		 11.26160908 113.54570007 13.60089874 9.5204668 114.93276215 15.1700058 9.50612354 113.27947998 14.67435455
		 8.083130836 114.72559357 16.053398132 8.013884544 113.17713165 15.60121918 7.9889946 111.52442169 15.1394577
		 6.4778533 111.79174805 16.18625641 6.42424822 110.1182251 15.86036682 5.3517065 110.36834717 16.53873444
		 5.3523283 108.51454163 16.26838684 5.31002617 108.59864807 16.99669647 5.42828465 106.75450134 16.9812851
		 6.6032939 107.060836792 16.50013733 6.65420485 105.2687149 16.33480072 7.13757086 105.41620636 15.89245605
		 7.33161116 103.56600189 15.91418457 8.7079401 103.82635498 14.47429657 8.63532257 105.74969482 14.63513947
		 9.69291019 103.98335266 13.77864075 9.75131893 101.93787384 13.68289185;
	setAttr ".vt[1826:1853]" 10.28330898 100.075790405 14.7261734 9.94269085 99.91885376 13.7042923
		 10.52896595 98.12272644 14.95494843 9.82037258 98.19648743 16.040420532 10.20107937 96.14360046 16.29200745
		 10.32993221 93.88528442 16.35238647 8.71059132 101.83058929 14.32807159 8.85697746 99.83663177 14.34386444
		 7.14360332 107.21179962 16.12940979 6.37905931 108.83403778 16.32553864 6.34185362 110.66392517 16.35561371
		 5.31458616 110.49502563 16.97505188 5.52095652 112.67843628 17.12905884 5.65613222 114.48130798 17.19200134
		 5.67795372 113.84578705 17.059364319 5.70730734 114.5037384 17.1852417 6.63698244 114.57055664 16.79089355
		 6.58954191 113.39543915 16.51076508 5.50819969 112.21338654 16.81468964 10.47415447 89.04057312 16.55083466
		 10.47588634 86.49533081 16.67215729 8.70773792 86.47581482 17.41714478 10.47567844 83.98051453 16.74032593
		 10.50925159 81.47045898 16.75636292 10.94725132 78.9149704 15.92845535 10.62730312 78.90026855 16.74845123
		 11.057850838 76.26719666 15.86488342 -0.5268563 105.37393951 17.62989807;
	setAttr -s 5231 ".ed";
	setAttr ".ed[0:165]"  0 1 1 1 2 1 2 0 1 2 3 1 3 0 1 3 4 1 4 0 1 4 5 1 5 0 1
		 4 6 0 6 5 1 6 7 0 7 5 1 1 5 1 7 1 1 7 8 0 8 1 1 8 9 1 9 1 1 8 10 1 10 9 1 10 11 1
		 11 9 1 2 9 1 11 2 1 11 12 1 12 2 1 11 13 1 13 12 1 13 14 1 14 12 1 14 3 1 3 12 1
		 14 15 1 15 3 1 16 15 1 14 16 1 17 16 1 14 17 1 17 18 1 18 16 1 18 19 1 19 16 1 19 20 1
		 20 16 1 19 21 1 21 20 1 22 21 1 19 22 1 19 23 1 23 22 1 23 24 1 24 22 1 23 25 1 25 24 1
		 23 26 1 26 25 1 26 27 1 27 25 1 28 27 1 26 28 1 29 28 1 26 29 1 29 18 1 18 28 1 18 30 1
		 30 28 1 31 28 1 30 31 1 30 32 1 32 31 1 32 33 1 33 31 1 34 31 1 33 34 1 33 35 1 35 34 1
		 33 36 1 36 35 1 37 35 1 36 37 1 36 38 1 38 37 1 38 39 1 39 37 1 38 40 1 40 39 1 40 41 1
		 41 39 1 41 42 0 42 39 1 42 43 1 43 39 1 42 44 0 44 43 1 44 45 1 45 43 1 46 43 1 45 46 1
		 47 46 1 45 47 1 45 48 1 48 47 1 48 49 1 49 47 1 50 47 1 49 50 1 51 50 1 49 51 1 49 52 1
		 52 51 1 53 51 1 52 53 1 54 53 1 52 54 1 52 55 1 55 54 1 55 56 1 56 54 1 55 57 1 57 56 0
		 55 48 1 48 57 1 48 58 1 58 57 0 56 59 0 59 54 1 59 60 1 60 54 1 59 61 0 61 60 1 62 60 1
		 61 62 1 61 63 0 63 62 1 63 64 1 64 62 1 64 65 1 65 62 1 53 62 1 65 53 1 65 66 1 66 53 1
		 65 67 1 67 66 1 65 68 1 68 67 1 69 67 1 68 69 1 70 69 1 68 70 1 68 71 1 71 70 1 68 64 1
		 64 71 1 72 71 1 64 72 1 72 73 0 73 71 1 73 74 1 74 71 1 73 75 0 75 74 1 75 76 1 76 74 1
		 77 74 1;
	setAttr ".ed[166:331]" 76 77 1 76 78 1 78 77 1 79 77 1 78 79 1 78 80 1 80 79 1
		 80 81 1 81 79 1 82 79 1 81 82 1 81 83 1 83 82 1 84 82 1 83 84 1 85 84 1 83 85 1 86 85 1
		 83 86 1 87 86 1 83 87 1 87 88 1 88 86 1 89 88 1 87 89 1 87 90 1 90 89 1 87 81 1 81 90 1
		 91 89 1 90 91 1 90 92 1 92 91 0 90 80 1 80 92 1 80 93 1 93 92 0 80 94 1 94 93 1 94 95 1
		 95 93 0 94 96 1 96 95 1 94 97 1 97 96 1 97 98 1 98 96 1 97 99 1 99 98 0 76 99 1 97 76 1
		 76 100 1 100 99 0 101 96 1 98 101 0 94 78 1 78 97 1 101 95 0 91 102 0 102 89 1 102 103 1
		 103 89 1 102 104 0 104 103 1 104 105 1 105 103 1 105 106 1 106 103 1 106 88 1 88 103 1
		 107 88 1 106 107 1 106 108 1 108 107 1 109 107 1 108 109 1 108 110 1 110 109 1 111 109 1
		 110 111 1 112 111 1 110 112 1 113 112 1 110 113 1 113 114 1 114 112 0 115 114 1 113 115 1
		 116 115 1 113 116 1 113 108 1 108 116 1 117 115 1 116 117 1 116 105 1 105 117 1 118 117 1
		 105 118 1 118 119 0 119 117 1 120 117 1 119 120 1 121 120 1 119 121 0 122 120 1 121 122 0
		 122 115 1 115 120 1 122 114 0 112 123 0 123 111 1 123 124 1 124 111 1 125 111 1 124 125 1
		 126 125 1 124 126 1 127 126 1 124 127 1 127 128 0 128 126 1 128 129 0 129 126 1 129 130 1
		 130 126 1 130 131 1 131 126 1 130 132 1 132 131 1 132 133 1 133 131 1 133 134 1 134 131 1
		 133 135 1 135 134 1 135 136 1 136 134 1 135 137 1 137 136 1 138 136 1 137 138 1 137 139 1
		 139 138 1 140 138 1 139 140 1 141 140 1 139 141 1 139 142 1 142 141 1 142 143 1 143 141 1
		 143 144 1 144 141 1 143 77 1 77 144 1 142 70 1 70 143 1 145 142 1 139 145 1 145 69 1
		 69 142 1 146 69 1 145 146 1 145 147 1 147 146 1 148 146 1;
	setAttr ".ed[332:497]" 147 148 1 149 148 1 147 149 1 135 149 1 147 135 1 149 150 1
		 150 148 1 150 151 1 151 148 1 150 152 1 152 151 1 152 66 1 66 151 1 152 51 1 51 66 1
		 27 152 1 150 27 1 27 153 1 153 152 1 154 153 1 27 154 1 154 34 1 34 153 1 155 153 1
		 34 155 1 155 50 1 50 153 1 50 152 1 149 25 1 25 150 1 151 146 1 151 67 1 67 146 1
		 145 137 1 137 147 1 144 140 1 144 82 1 82 140 1 140 84 1 84 138 1 84 156 1 156 138 1
		 156 136 1 156 134 1 156 157 1 157 134 1 156 85 1 85 157 1 158 157 1 85 158 1 158 159 1
		 159 157 1 159 125 1 125 157 1 158 109 1 109 159 1 125 134 1 133 149 1 133 24 1 24 149 1
		 125 131 1 132 24 1 160 132 1 130 160 1 161 160 1 130 161 1 161 162 0 162 160 1 162 21 1
		 21 160 1 162 163 0 163 21 1 160 22 1 22 132 1 129 161 0 159 111 1 123 127 0 158 107 1
		 158 86 1 86 107 1 106 116 1 104 118 0 144 79 1 143 74 1 75 100 0 143 71 1 63 72 0
		 53 60 1 49 55 1 155 47 1 45 58 1 155 46 1 155 35 1 35 46 1 46 37 1 37 43 1 44 58 0
		 164 41 1 40 164 1 165 164 1 40 165 1 166 165 1 40 166 1 167 165 1 166 167 1 168 167 1
		 166 168 1 166 169 1 169 168 1 169 170 1 170 168 1 171 168 1 170 171 1 170 172 1 172 171 0
		 173 172 1 170 173 1 174 173 1 170 174 1 174 175 1 175 173 1 175 10 1 10 173 1 176 173 1
		 10 176 1 175 177 1 177 10 1 175 178 1 178 177 1 13 177 1 178 13 1 178 17 1 17 13 1
		 178 30 1 30 17 1 175 32 1 32 178 1 174 32 1 179 32 1 174 179 1 169 179 1 174 169 1
		 169 36 1 36 179 1 176 172 0 171 180 0 180 168 1 166 38 1 38 169 1 180 167 1 180 181 1
		 181 167 1 181 182 1 182 167 1 181 183 1 183 182 1 184 182 1 183 184 1 183 185 1 185 184 1
		 185 186 1 186 184 1 186 187 0 187 184 1 187 188 1 188 184 1;
	setAttr ".ed[498:663]" 187 189 0 189 188 1 164 188 1 189 164 1 189 190 0 190 164 1
		 191 186 0 185 191 1 185 192 1 192 191 1 193 191 1 192 193 1 194 193 1 192 194 1 195 194 1
		 192 195 1 192 196 1 196 195 1 196 197 1 197 195 0 196 198 1 198 197 0 196 183 1 183 198 1
		 195 199 0 199 194 1 200 194 1 199 200 0 201 194 1 200 201 1 200 202 1 202 201 1 203 201 1
		 202 203 1 202 204 1 204 203 1 205 203 0 204 205 1 206 205 0 204 206 0 202 207 1 207 204 0
		 203 208 0 208 201 1 209 201 1 208 209 0 209 193 1 193 201 1 200 207 0 209 191 0 185 196 1
		 188 182 1 188 165 1 165 182 1 181 198 1 181 210 1 210 198 0 180 210 0 190 41 0 33 179 1
		 154 31 1 154 28 1 23 29 1 19 29 1 163 20 1 163 211 0 211 20 1 211 15 1 15 20 1 212 15 1
		 211 212 0 212 3 1 11 177 1 8 176 0 212 4 0 213 214 0 214 215 1 215 213 1 216 213 0
		 215 216 1 215 217 1 217 216 1 217 218 1 218 216 0 217 219 1 219 218 1 219 220 1 220 218 0
		 219 221 1 221 220 1 221 222 1 222 220 0 221 223 1 223 222 1 224 223 1 221 224 1 225 224 1
		 221 225 1 226 224 1 225 226 1 225 227 1 227 226 1 227 228 1 228 226 1 228 229 1 229 226 1
		 229 230 1 230 226 1 229 231 1 231 230 1 231 232 1 232 230 1 232 233 1 233 230 1 232 234 1
		 234 233 1 235 233 1 234 235 1 234 236 1 236 235 1 234 237 1 237 236 1 237 238 1 238 236 1
		 237 239 1 239 238 1 240 238 1 239 240 1 239 241 1 241 240 1 242 240 1 241 242 1 241 243 1
		 243 242 1 244 242 1 243 244 1 243 245 1 245 244 1 246 244 1 245 246 1 245 247 1 247 246 1
		 248 246 1 247 248 1 247 249 1 249 248 1 250 248 1 249 250 1 251 250 1 249 251 1 249 252 1
		 252 251 1 252 253 1 253 251 1 254 251 1 253 254 1 253 255 1 255 254 1 256 254 1 255 256 1
		 255 257 1 257 256 1 255 258 1 258 257 1 258 259 1 259 257 1;
	setAttr ".ed[664:829]" 259 260 1 260 257 1 260 261 1 261 257 1 260 262 1 262 261 1
		 263 262 1 260 263 1 260 264 1 264 263 1 265 263 1 264 265 1 264 266 1 266 265 1 266 267 1
		 267 265 1 267 268 1 268 265 1 269 265 1 268 269 1 268 270 1 270 269 1 271 269 1 270 271 0
		 271 272 1 272 269 1 271 273 1 273 272 1 271 274 0 274 273 1 274 275 1 275 273 1 276 273 1
		 275 276 1 277 276 1 275 277 1 275 278 1 278 277 1 275 279 1 279 278 1 280 278 1 279 280 0
		 280 281 1 281 278 1 280 282 0 282 281 0 275 283 1 283 279 0 281 277 0 277 284 0 284 276 1
		 284 285 1 285 276 1 284 286 1 286 285 1 287 285 1 286 287 1 286 288 1 288 287 1 289 287 1
		 288 289 1 288 263 1 263 289 1 289 272 1 272 287 1 286 290 1 290 288 1 291 288 1 290 291 1
		 292 291 1 290 292 1 290 293 1 293 292 0 292 294 0 294 291 1 295 291 1 294 295 0 295 296 1
		 296 291 1 262 291 1 296 262 1 297 296 1 295 297 0 297 298 1 298 296 1 298 261 1 261 296 1
		 298 256 1 256 261 1 299 256 1 298 299 1 298 300 1 300 299 1 301 299 1 300 301 0 301 302 1
		 302 299 1 303 299 1 302 303 1 304 303 1 302 304 1 305 304 1 302 305 1 302 306 1 306 305 1
		 306 307 1 307 305 1 308 305 1 307 308 1 307 309 1 309 308 1 310 308 1 309 310 1 309 311 1
		 311 310 1 312 310 1 311 312 1 311 313 1 313 312 1 314 312 1 313 314 1 313 315 1 315 314 1
		 316 314 1 315 316 1 315 317 1 317 316 1 315 318 1 318 317 0 315 319 1 319 318 1 319 320 1
		 320 318 0 319 321 1 321 320 1 321 322 1 322 320 0 321 323 1 323 322 1 324 322 0 323 324 1
		 325 324 1 323 325 1 323 326 1 326 325 1 326 327 1 327 325 1 326 328 1 328 327 0 326 329 1
		 329 328 1 329 330 1 330 328 0 329 331 1 331 330 1 331 332 1 332 330 0 331 307 1 307 332 1
		 329 333 1 333 331 1 333 309 1 309 331 1 329 334 1 334 333 1 334 335 1;
	setAttr ".ed[830:995]" 335 333 1 335 311 1 311 333 1 321 335 1 334 321 1 326 334 1
		 336 325 1 327 336 0 323 334 1 336 324 0 319 335 1 319 313 1 313 335 1 337 316 1 317 337 0
		 338 316 1 337 338 1 339 338 1 337 339 0 240 338 1 339 240 1 340 240 1 339 340 0 338 341 1
		 341 316 1 338 242 1 242 341 1 341 314 1 341 342 1 342 314 1 341 244 1 244 342 1 342 312 1
		 342 343 1 343 312 1 342 246 1 246 343 1 343 310 1 343 344 1 344 310 1 343 248 1 248 344 1
		 344 308 1 344 345 1 345 308 1 344 250 1 250 345 1 250 346 1 346 345 1 346 304 1 304 345 1
		 254 304 1 346 254 1 345 305 1 306 332 0 254 303 1 301 306 0 303 256 1 297 300 0 262 288 1
		 286 293 1 272 285 1 284 293 0 285 273 1 274 283 0 289 269 1 268 347 1 347 270 0 268 348 1
		 348 347 0 289 265 1 267 348 1 267 349 1 349 348 0 350 349 1 267 350 1 350 351 1 351 349 0
		 350 352 1 352 351 1 352 353 1 353 351 0 352 354 1 354 353 1 354 355 1 355 353 0 356 355 1
		 354 356 1 357 356 1 354 357 1 358 357 1 354 358 1 358 359 1 359 357 1 360 357 1 359 360 1
		 359 361 1 361 360 1 362 360 1 361 362 1 361 363 1 363 362 1 364 362 1 363 364 1 363 365 1
		 365 364 1 366 364 1 365 366 1 367 366 1 365 367 1 365 368 1 368 367 1 368 369 1 369 367 1
		 369 370 1 370 367 1 371 367 1 370 371 1 372 371 1 370 372 1 373 372 1 370 373 1 374 373 1
		 370 374 1 374 375 1 375 373 1 376 373 1 375 376 1 377 376 1 375 377 1 375 378 1 378 377 1
		 378 379 1 379 377 1 378 380 1 380 379 1 237 379 1 380 237 1 378 381 1 381 380 1 382 380 1
		 381 382 1 381 383 1 383 382 1 384 382 1 383 384 1 383 385 1 385 384 1 385 386 1 386 384 1
		 386 387 1 387 384 1 386 388 1 388 387 1 389 388 1 386 389 1 386 390 1 390 389 1 390 391 1
		 391 389 1 391 247 1 247 389 1 391 392 1 392 247 1 391 393 1 393 392 1;
	setAttr ".ed[996:1161]" 391 394 1 394 393 1 394 395 1 395 393 1 396 393 1 395 396 1
		 395 397 1 397 396 1 398 396 1 397 398 1 397 258 1 258 398 1 397 399 1 399 258 1 400 399 1
		 397 400 1 400 401 1 401 399 1 402 401 1 400 402 1 400 403 1 403 402 1 404 402 1 403 404 1
		 403 405 1 405 404 1 406 404 1 405 406 1 405 407 1 407 406 1 408 406 1 407 408 1 407 409 1
		 409 408 1 410 408 1 409 410 1 409 378 1 378 410 1 410 374 1 374 408 1 374 411 1 411 408 1
		 374 369 1 369 411 1 407 383 1 383 409 1 411 406 1 411 412 1 412 406 1 411 368 1 368 412 1
		 368 413 1 413 412 1 414 412 1 413 414 1 413 415 1 415 414 1 416 414 1 415 416 1 415 417 1
		 417 416 1 418 416 1 417 418 1 417 419 1 419 418 1 420 418 1 419 420 1 419 421 1 421 420 1
		 421 266 1 266 420 1 350 266 1 421 350 1 419 422 1 422 421 1 422 358 1 358 421 1 358 352 1
		 352 421 1 420 423 1 423 418 1 423 401 1 401 418 1 420 259 1 259 423 1 259 399 1 399 423 1
		 420 264 1 264 259 1 417 422 1 417 424 1 424 422 1 424 359 1 359 422 1 401 416 1 415 424 1
		 415 425 1 425 424 1 425 361 1 361 424 1 416 402 1 402 414 1 413 425 1 413 426 1 426 425 1
		 426 363 1 363 425 1 414 404 1 404 412 1 368 426 1 405 385 1 385 407 1 394 385 1 405 394 1
		 394 390 1 390 385 1 403 394 1 400 395 1 395 403 1 398 253 1 253 396 1 396 252 1 252 393 1
		 252 392 1 389 245 1 245 388 1 388 427 1 427 387 1 428 387 1 427 428 1 427 239 1 239 428 1
		 380 428 1 239 380 1 428 382 1 382 387 1 388 243 1 243 427 1 381 409 1 379 232 1 232 377 1
		 375 410 1 377 231 1 231 376 1 429 376 1 231 429 1 430 376 1 429 430 1 429 431 1 431 430 1
		 431 432 1 432 430 1 431 433 1 433 432 1 434 432 1 433 434 1 433 435 1 435 434 1 435 436 1
		 436 434 1 436 437 1 437 434 1 436 438 1 438 437 1 439 437 1 438 439 1;
	setAttr ".ed[1162:1327]" 438 440 1 440 439 1 440 441 1 441 439 1 372 439 1 441 372 1
		 372 442 1 442 439 1 443 442 1 372 443 1 443 430 1 430 442 1 440 444 1 444 441 1 445 444 1
		 440 445 1 440 446 1 446 445 1 446 447 1 447 445 1 448 447 1 446 448 1 446 436 1 436 448 1
		 449 448 1 436 449 1 449 450 0 450 448 1 450 451 1 451 448 1 450 452 0 452 451 1 452 453 1
		 453 451 1 454 451 1 453 454 1 455 454 1 453 455 1 456 455 1 453 456 1 456 457 0 457 455 1
		 457 458 1 458 455 1 458 459 1 459 455 1 458 460 1 460 459 1 461 459 1 460 461 1 460 462 1
		 462 461 1 462 463 1 463 461 1 464 461 1 463 464 1 465 464 1 463 465 1 463 466 1 466 465 1
		 466 467 1 467 465 1 467 468 1 468 465 1 468 469 1 469 465 1 468 470 1 470 469 1 471 470 1
		 468 471 1 468 472 1 472 471 1 472 473 1 473 471 1 474 473 1 472 474 1 472 475 1 475 474 0
		 467 475 1 472 467 1 467 476 1 476 475 0 474 477 0 477 473 1 356 473 1 477 356 1 478 473 1
		 356 478 1 478 471 1 479 471 1 478 479 1 360 479 1 478 360 1 479 470 1 480 470 1 479 480 1
		 362 480 1 479 362 1 481 470 1 480 481 1 482 481 1 480 482 1 364 482 1 480 364 1 483 481 1
		 482 483 1 444 483 1 482 444 1 366 444 1 482 366 1 371 444 1 366 371 1 483 484 1 484 481 1
		 483 485 1 485 484 1 486 484 1 485 486 1 485 454 1 454 486 1 454 459 1 459 486 1 485 447 1
		 447 454 1 486 464 1 464 484 1 469 484 1 464 469 1 483 445 1 445 485 1 469 481 1 466 476 1
		 466 487 1 487 476 0 466 462 1 462 487 1 462 488 1 488 487 0 486 461 1 460 488 1 460 489 1
		 489 488 0 458 489 1 458 490 1 490 489 0 458 491 1 491 490 0 457 491 0 447 451 1 452 456 0
		 371 441 1 438 446 1 442 437 1 442 432 1 432 437 1 435 449 0 433 492 1 492 435 0 433 493 1
		 493 492 1 493 494 1 494 492 0 493 495 1 495 494 1 493 496 1 496 495 1;
	setAttr ".ed[1328:1493]" 228 495 1 496 228 1 228 497 1 497 495 1 498 495 1 497 498 1
		 497 499 1 499 498 0 497 500 1 500 499 1 497 227 1 227 500 1 227 501 1 501 500 1 501 502 1
		 502 500 1 503 500 1 502 503 1 502 214 1 214 503 0 217 502 1 501 217 1 503 499 0 493 431 1
		 431 496 1 498 494 0 429 496 1 229 496 1 429 229 1 443 376 1 443 373 1 365 426 1 478 357 1
		 477 355 0 255 398 1 346 251 1 249 392 1 241 427 1 340 238 1 340 236 1 340 504 0 504 236 1
		 234 379 1 504 235 1 504 505 0 505 235 1 505 223 1 223 235 1 223 233 1 224 230 1 233 224 1
		 225 501 1 219 501 1 225 219 1 505 222 0 215 502 1 506 507 1 507 508 1 508 506 1 508 509 1
		 509 506 1 509 510 1 510 506 1 510 511 1 511 506 1 512 506 1 511 512 1 511 513 1 513 512 1
		 513 514 1 514 512 1 513 515 1 515 514 0 516 515 1 513 516 1 513 517 1 517 516 1 517 518 1
		 518 516 1 518 519 1 519 516 1 518 520 1 520 519 0 518 521 1 521 520 0 518 522 1 522 521 1
		 523 521 0 522 523 1 522 524 1 524 523 1 524 525 1 525 523 0 524 526 1 526 525 1 527 526 1
		 524 527 1 524 528 1 528 527 1 529 527 1 528 529 1 528 530 1 530 529 1 531 529 1 530 531 1
		 530 532 1 532 531 1 533 532 1 530 533 1 517 532 1 533 517 1 517 534 1 534 532 1 535 532 1
		 534 535 1 511 535 1 534 511 1 535 531 1 510 531 1 535 510 1 510 536 1 536 531 1 536 537 1
		 537 531 1 536 538 1 538 537 1 538 539 1 539 537 1 540 537 1 539 540 1 539 541 1 541 540 1
		 542 540 1 541 542 1 543 542 1 541 543 1 541 544 1 544 543 1 544 545 1 545 543 1 546 543 1
		 545 546 1 545 547 1 547 546 1 548 546 1 547 548 1 547 549 1 549 548 0 547 550 1 550 549 1
		 551 550 1 547 551 1 551 552 1 552 550 1 552 553 1 553 550 1 554 550 1 553 554 1 553 555 1
		 555 554 0 553 556 1 556 555 1 557 556 1 553 557 1 557 558 1 558 556 1;
	setAttr ".ed[1494:1659]" 558 559 1 559 556 1 560 556 1 559 560 1 559 561 1 561 560 0
		 559 562 1 562 561 1 563 562 1 559 563 1 563 564 1 564 562 1 564 565 1 565 562 1 566 562 1
		 565 566 1 565 567 1 567 566 0 565 568 1 568 567 1 565 569 1 569 568 1 569 570 1 570 568 1
		 571 568 1 570 571 1 570 572 1 572 571 1 572 573 1 573 571 1 572 574 1 574 573 1 574 575 1
		 575 573 1 576 573 1 575 576 1 577 576 1 575 577 1 578 577 1 575 578 1 578 579 1 579 577 1
		 579 580 1 580 577 1 581 577 1 580 581 1 582 581 0 580 582 1 580 583 1 583 582 1 580 584 1
		 584 583 1 585 583 1 584 585 1 584 586 1 586 585 1 586 587 1 587 585 1 586 588 1 588 587 1
		 589 587 1 588 589 1 588 590 1 590 589 0 588 591 1 591 590 1 588 592 1 592 591 1 592 593 1
		 593 591 1 593 594 1 594 591 1 593 595 1 595 594 1 593 596 1 596 595 1 596 597 1 597 595 1
		 598 595 1 597 598 1 597 599 1 599 598 1 600 598 1 599 600 1 599 601 1 601 600 1 601 602 1
		 602 600 1 601 603 1 603 602 1 604 602 1 603 604 1 603 605 1 605 604 1 605 606 1 606 604 1
		 605 607 1 607 606 1 607 608 1 608 606 1 609 606 1 608 609 1 608 610 1 610 609 1 610 611 1
		 611 609 1 611 612 1 612 609 1 611 613 1 613 612 1 613 614 1 614 612 1 613 615 1 615 614 1
		 615 616 1 616 614 1 615 617 1 617 616 1 618 616 1 617 618 1 617 619 1 619 618 1 620 618 1
		 619 620 1 621 620 1 619 621 1 619 622 1 622 621 1 623 622 1 619 623 1 623 624 1 624 622 1
		 625 624 1 623 625 1 623 626 1 626 625 1 627 625 1 626 627 1 628 627 1 626 628 1 615 628 1
		 626 615 1 629 628 1 615 629 1 630 628 1 629 630 1 629 631 1 631 630 1 631 632 1 632 630 1
		 632 633 1 633 630 1 633 634 1 634 630 1 633 635 1 635 634 1 636 635 1 633 636 1 633 637 1
		 637 636 1 637 638 1 638 636 1 638 639 1 639 636 1 639 640 1 640 636 1;
	setAttr ".ed[1660:1825]" 639 641 1 641 640 1 639 642 1 642 641 1 643 641 1 642 643 1
		 642 644 1 644 643 1 645 643 1 644 645 1 644 646 1 646 645 1 646 647 1 647 645 1 647 648 1
		 648 645 1 648 649 1 649 645 1 648 650 1 650 649 1 651 649 1 650 651 1 652 651 1 650 652 1
		 650 653 1 653 652 1 653 654 1 654 652 1 654 655 1 655 652 1 655 656 1 656 652 1 655 657 1
		 657 656 1 657 658 1 658 656 1 658 651 1 651 656 1 658 659 1 659 651 1 659 660 1 660 651 1
		 659 661 1 661 660 1 661 662 1 662 660 1 643 660 1 662 643 1 643 649 1 649 660 1 661 663 1
		 663 662 1 663 641 1 641 662 1 664 663 1 661 664 1 661 665 1 665 664 1 666 664 1 665 666 1
		 665 667 1 667 666 1 668 666 1 667 668 1 667 669 1 669 668 1 670 668 1 669 670 1 669 671 1
		 671 670 1 672 670 1 671 672 1 671 673 1 673 672 1 674 672 1 673 674 1 673 675 1 675 674 1
		 675 676 1 676 674 1 677 674 1 676 677 1 676 678 1 678 677 1 676 679 1 679 678 1 679 680 1
		 680 678 1 681 680 1 679 681 1 682 681 1 679 682 1 679 683 1 683 682 1 683 684 1 684 682 1
		 685 682 1 684 685 1 686 685 1 684 686 1 684 687 1 687 686 0 684 688 1 688 687 1 689 687 1
		 688 689 1 688 690 1 690 689 1 691 689 1 690 691 1 690 692 1 692 691 1 693 691 1 692 693 1
		 692 694 1 694 693 1 695 693 1 694 695 1 694 696 1 696 695 1 697 695 1 696 697 1 696 698 1
		 698 697 1 658 697 1 698 658 1 658 699 1 699 697 1 699 700 1 700 697 1 699 701 1 701 700 1
		 699 702 1 702 701 1 702 703 1 703 701 1 703 704 1 704 701 1 705 701 1 704 705 1 704 706 1
		 706 705 1 706 707 1 707 705 1 707 700 1 700 705 1 707 695 1 695 700 1 706 708 1 708 707 1
		 706 709 1 709 708 1 710 708 1 709 710 1 709 711 1 711 710 1 712 710 1 711 712 0 712 713 1
		 713 710 1 713 714 1 714 710 1 713 691 1 691 714 1 715 713 1 712 715 0;
	setAttr ".ed[1826:1991]" 715 689 1 689 713 1 709 716 1 716 711 0 717 716 1 709 717 1
		 717 718 1 718 716 0 719 718 1 717 719 1 717 720 1 720 719 1 721 719 1 720 721 1 720 703 1
		 703 721 1 703 722 1 722 721 1 722 723 1 723 721 1 723 724 1 724 721 1 723 725 1 725 724 1
		 726 724 1 725 726 0 726 719 1 719 724 1 723 727 1 727 725 0 728 727 1 723 728 1 728 729 1
		 729 727 0 730 729 1 728 730 1 728 731 1 731 730 1 731 732 1 732 730 1 733 730 1 732 733 1
		 732 734 1 734 733 0 732 735 1 735 734 1 736 735 1 732 736 1 737 735 1 736 737 1 738 737 1
		 736 738 1 736 739 1 739 738 1 740 738 1 739 740 1 741 740 1 739 741 1 739 742 1 742 741 1
		 742 743 1 743 741 1 744 741 1 743 744 1 743 702 1 702 744 1 657 744 1 702 657 1 745 741 1
		 744 745 1 655 745 1 744 655 1 742 722 1 722 743 1 742 728 1 728 722 1 739 731 1 731 742 1
		 745 740 1 654 740 1 745 654 1 654 746 1 746 740 1 746 747 1 747 740 1 746 748 1 748 747 1
		 749 748 1 746 749 1 746 653 1 653 749 1 648 749 1 653 648 1 750 748 1 749 750 1 647 750 1
		 749 647 1 647 751 1 751 750 1 751 752 1 752 750 1 752 753 1 753 750 1 752 754 1 754 753 1
		 755 753 1 754 755 1 754 756 1 756 755 1 756 757 1 757 755 1 757 758 1 758 755 1 758 759 1
		 759 755 1 758 760 1 760 759 1 760 747 1 747 759 1 760 738 1 738 747 1 761 760 1 758 761 1
		 758 762 1 762 761 1 762 763 1 763 761 1 763 764 1 764 761 1 764 737 1 737 761 1 765 764 1
		 763 765 1 763 766 1 766 765 0 763 767 1 767 766 1 767 768 1 768 766 0 767 769 1 769 768 1
		 770 769 1 767 770 1 767 762 1 762 770 1 757 770 1 762 757 1 757 771 1 771 770 1 771 772 1
		 772 770 1 771 773 1 773 772 1 771 774 1 774 773 1 775 773 1 774 775 1 776 775 1 774 776 1
		 774 777 1 777 776 1 777 778 1 778 776 1 779 776 1 778 779 1 780 779 1;
	setAttr ".ed[1992:2157]" 778 780 1 778 781 1 781 780 1 782 780 1 781 782 1 781 783 1
		 783 782 1 781 784 1 784 783 1 784 785 1 785 783 1 784 751 1 751 785 1 751 646 1 646 785 1
		 786 785 1 646 786 1 786 787 1 787 785 1 788 787 1 786 788 1 786 789 1 789 788 1 786 644 1
		 644 789 1 790 788 1 789 790 1 789 791 1 791 790 1 792 790 1 791 792 1 638 792 1 791 638 1
		 793 792 1 638 793 1 793 794 1 794 792 1 795 794 1 793 795 1 796 795 1 793 796 1 793 637 1
		 637 796 1 637 632 1 632 796 1 797 796 1 632 797 1 797 798 1 798 796 1 797 799 1 799 798 1
		 800 799 1 797 800 1 797 631 1 631 800 1 801 800 1 631 801 1 801 802 1 802 800 1 801 610 1
		 610 802 1 803 802 1 610 803 1 803 804 1 804 802 1 805 802 1 804 805 1 806 805 1 804 806 1
		 807 806 1 804 807 1 804 808 1 808 807 1 809 807 1 808 809 1 808 810 1 810 809 1 808 607 1
		 607 810 1 808 803 1 803 607 1 811 809 1 810 811 1 810 812 1 812 811 1 810 605 1 605 812 1
		 813 811 1 812 813 1 814 813 1 812 814 1 603 814 1 812 603 1 814 815 1 815 813 1 816 813 1
		 815 816 1 817 816 1 815 817 1 815 818 1 818 817 1 819 817 1 818 819 1 818 820 1 820 819 1
		 821 819 1 820 821 1 820 822 1 822 821 1 822 823 1 823 821 1 824 821 1 823 824 1 825 824 1
		 823 825 1 823 826 1 826 825 1 826 584 1 584 825 1 825 579 1 579 824 1 579 827 1 827 824 1
		 828 824 1 827 828 1 827 829 1 829 828 1 830 828 1 829 830 1 829 831 1 831 830 1 831 832 1
		 832 830 1 832 833 1 833 830 1 833 834 1 834 830 1 833 817 1 817 834 1 832 835 1 835 833 1
		 835 816 1 816 833 1 835 836 1 836 816 1 835 837 1 837 836 1 837 838 1 838 836 1 838 811 1
		 811 836 1 837 839 1 839 838 1 840 838 1 839 840 1 839 841 1 841 840 1 841 842 1 842 840 1
		 842 807 1 807 840 1 841 843 1 843 842 1 843 844 1 844 842 1 844 806 1;
	setAttr ".ed[2158:2323]" 806 842 1 844 845 1 845 806 1 846 845 1 844 846 1 847 846 1
		 844 847 1 847 848 1 848 846 1 848 849 1 849 846 1 849 850 1 850 846 1 849 851 1 851 850 1
		 851 798 1 798 850 1 851 795 1 795 798 1 851 852 1 852 795 1 851 853 1 853 852 1 853 854 1
		 854 852 1 854 855 1 855 852 1 855 794 1 794 852 1 856 794 1 855 856 1 855 857 1 857 856 1
		 858 856 1 857 858 1 857 859 1 859 858 1 860 858 1 859 860 1 859 861 1 861 860 1 862 860 1
		 861 862 1 861 863 1 863 862 1 782 862 1 863 782 1 863 864 1 864 782 1 863 865 1 865 864 1
		 866 865 1 863 866 1 866 867 1 867 865 1 867 868 1 868 865 1 869 865 1 868 869 1 868 870 1
		 870 869 1 870 871 1 871 869 1 871 872 1 872 869 1 872 864 1 864 869 1 872 780 1 780 864 1
		 873 872 1 871 873 1 871 874 1 874 873 1 874 875 1 875 873 1 875 876 1 876 873 1 876 779 1
		 779 873 1 877 876 1 875 877 1 875 878 1 878 877 1 878 879 1 879 877 1 879 775 1 775 877 1
		 878 880 1 880 879 1 881 880 1 878 881 1 882 881 1 878 882 1 878 883 1 883 882 1 883 884 1
		 884 882 1 885 882 1 884 885 1 886 885 1 884 886 1 884 887 1 887 886 1 888 886 1 887 888 1
		 887 889 1 889 888 1 887 890 1 890 889 1 891 889 1 890 891 1 890 892 1 892 891 1 890 893 1
		 893 892 1 894 892 1 893 894 1 893 895 1 895 894 1 896 894 1 895 896 1 897 896 1 895 897 1
		 895 898 1 898 897 1 898 899 1 899 897 1 900 897 1 899 900 1 901 900 1 899 901 1 899 902 1
		 902 901 1 902 903 1 903 901 1 904 901 1 903 904 1 903 905 1 905 904 1 906 904 1 905 906 1
		 905 907 1 907 906 1 908 906 1 907 908 1 907 909 1 909 908 1 910 908 1 909 910 1 909 911 1
		 911 910 1 912 910 1 911 912 1 911 848 1 848 912 1 913 912 1 848 913 1 913 914 1 914 912 1
		 914 915 1 915 912 1 914 916 1 916 915 1 917 916 1 914 917 1 914 918 1;
	setAttr ".ed[2324:2489]" 918 917 1 919 917 1 918 919 1 920 919 1 918 920 1 913 920 1
		 918 913 1 913 921 1 921 920 1 913 847 1 847 921 1 843 921 1 847 843 1 843 922 1 922 921 1
		 923 921 1 922 923 1 922 924 1 924 923 1 925 923 1 924 925 1 926 925 1 924 926 1 924 927 1
		 927 926 1 928 926 1 927 928 1 927 929 1 929 928 1 832 928 1 929 832 1 930 929 1 927 930 1
		 927 931 1 931 930 1 931 839 1 839 930 1 930 837 1 837 929 1 932 926 1 928 932 1 928 831 1
		 831 932 1 933 932 1 831 933 1 933 934 1 934 932 1 934 935 1 935 932 1 934 936 1 936 935 1
		 936 937 1 937 935 1 925 935 1 937 925 1 937 938 1 938 925 1 937 939 1 939 938 1 940 939 1
		 937 940 1 940 941 1 941 939 1 941 942 1 942 939 1 943 939 1 942 943 1 942 919 1 919 943 1
		 942 944 1 944 919 1 945 944 1 942 945 1 945 946 1 946 944 1 946 947 1 947 944 1 948 944 1
		 947 948 1 947 949 1 949 948 1 949 950 1 950 948 1 950 917 1 917 948 1 949 951 1 951 950 1
		 951 952 1 952 950 1 952 916 1 916 950 1 953 916 1 952 953 1 952 954 1 954 953 1 955 953 1
		 954 955 1 954 956 1 956 955 1 957 955 1 956 957 1 956 958 1 958 957 1 959 957 1 958 959 1
		 958 960 1 960 959 1 961 959 1 960 961 1 960 962 1 962 961 1 963 961 1 962 963 1 962 964 1
		 964 963 1 896 963 1 964 896 1 964 965 1 965 896 1 964 966 1 966 965 1 964 967 1 967 966 1
		 968 966 1 967 968 1 969 968 1 967 969 1 970 969 1 967 970 1 967 962 1 962 970 1 971 969 1
		 970 971 1 970 972 1 972 971 1 973 971 1 972 973 1 972 974 1 974 973 1 975 973 1 974 975 1
		 974 976 1 976 975 1 977 975 1 976 977 1 976 978 1 978 977 1 979 977 1 978 979 1 978 951 1
		 951 979 1 980 979 1 951 980 1 980 981 1 981 979 1 982 981 1 980 982 1 980 983 1 983 982 1
		 984 982 1 983 984 1 985 984 1 983 985 1 983 947 1 947 985 1 552 984 1;
	setAttr ".ed[2490:2655]" 985 552 1 985 557 1 557 552 1 985 946 1 946 557 1 984 986 1
		 986 982 1 986 987 1 987 982 1 986 544 1 544 987 1 544 988 1 988 987 1 989 987 1 988 989 1
		 988 990 1 990 989 1 991 989 1 990 991 1 990 992 1 992 991 1 993 991 1 992 993 1 992 994 1
		 994 993 1 995 993 1 994 995 1 994 996 1 996 995 1 997 995 1 996 997 1 996 998 1 998 997 1
		 998 999 1 999 997 1 999 1000 1 1000 997 1 1001 997 1 1000 1001 1 1000 971 1 971 1001 1
		 1002 1000 1 999 1002 1 999 1003 1 1003 1002 1 1004 1002 1 1003 1004 1 1005 1004 1
		 1003 1005 1 1006 1005 1 1003 1006 1 1006 1007 1 1007 1005 1 1008 1007 1 1006 1008 1
		 1006 998 1 998 1008 1 1009 1008 1 998 1009 1 1009 1010 1 1010 1008 1 508 1010 1 1009 508 1
		 1009 1011 1 1011 508 1 1009 996 1 996 1011 1 1010 1012 1 1012 1008 1 1010 1013 1
		 1013 1012 1 1013 1014 1 1014 1012 1 1014 1007 1 1007 1012 1 1014 1015 1 1015 1007 1
		 1016 1015 1 1014 1016 1 1014 1017 1 1017 1016 1 1017 1018 1 1018 1016 1 1019 1016 1
		 1018 1019 0 1019 1020 1 1020 1016 1 1019 1021 1 1021 1020 1 1022 1020 1 1021 1022 1
		 1021 1023 1 1023 1022 1 1024 1022 1 1023 1024 1 1023 1025 1 1025 1024 1 1025 1026 1
		 1026 1024 1 1025 1027 1 1027 1026 1 1027 966 1 966 1026 1 1025 1028 1 1028 1027 1
		 1028 1029 1 1029 1027 1 1029 1030 1 1030 1027 1 1030 965 1 965 1027 1 1030 894 1
		 894 965 1 891 1030 1 1029 891 1 1031 891 1 1029 1031 1 1032 1031 1 1029 1032 1 1033 1031 1
		 1032 1033 1 1034 1033 1 1032 1034 1 1032 1035 1 1035 1034 1 1032 1028 1 1028 1035 1
		 1035 1036 1 1036 1034 1 1037 1034 1 1036 1037 1 1036 1038 1 1038 1037 0 1036 1039 1
		 1039 1038 1 1036 1040 1 1040 1039 1 1040 1023 1 1023 1039 1 1039 1041 1 1041 1038 0
		 1039 1021 1 1021 1041 1 1037 1042 0 1042 1034 1 1035 1040 1 1035 1025 1 1025 1040 1
		 1042 1033 1 1042 1043 0 1043 1033 1 1044 1033 1 1043 1044 0 1044 1045 1 1045 1033 1
		 1046 1045 1 1044 1046 0 1046 1047 1 1047 1045 1 888 1045 1 1047 888 1 888 1031 1
		 1031 1045 1 1046 1048 1 1048 1047 1 1048 886 1;
	setAttr ".ed[2656:2821]" 886 1047 1 1046 1049 0 1049 1048 1 1049 1050 1 1050 1048 1
		 1050 885 1 885 1048 1 1050 1051 1 1051 885 1 1050 1052 1 1052 1051 1 1053 1052 1
		 1050 1053 1 1053 1054 0 1054 1052 1 1055 1052 1 1054 1055 0 1055 1056 1 1056 1052 1
		 1057 1056 1 1055 1057 0 1057 1058 1 1058 1056 1 1059 1056 1 1058 1059 1 1058 1060 1
		 1060 1059 1 1060 1061 1 1061 1059 1 1060 1062 1 1062 1061 1 1063 1061 1 1062 1063 1
		 1062 1064 1 1064 1063 1 1064 1065 0 1065 1063 1 1065 1066 1 1066 1063 1 1066 1067 1
		 1067 1063 1 1066 1068 1 1068 1067 1 879 1067 1 1068 879 1 1068 773 1 773 879 1 769 1068 1
		 1066 769 1 769 772 1 772 1068 1 1065 768 0 768 1066 1 1062 1069 1 1069 1064 0 1070 1069 1
		 1062 1070 1 1070 1071 1 1071 1069 0 1072 1071 1 1070 1072 1 1070 1073 1 1073 1072 1
		 1073 1074 1 1074 1072 1 1074 1075 1 1075 1072 1 1074 1076 0 1076 1075 0 1073 1077 1
		 1077 1074 0 1058 1077 1 1073 1058 1 1070 1060 1 1060 1073 1 1075 1071 0 1067 1061 1
		 1067 1078 1 1078 1061 1 1067 880 1 880 1078 1 1078 1059 1 1078 1079 1 1079 1059 1
		 1078 881 1 881 1079 1 1051 1079 1 881 1051 1 1079 1056 1 1057 1077 0 1079 1052 1
		 1049 1053 0 888 891 1 1026 1004 1 1004 1024 1 1026 968 1 968 1004 1 1024 1005 1 1005 1022 1
		 1015 1022 1 1005 1015 1 1015 1020 1 1019 1041 0 1017 1080 1 1080 1018 0 1017 1081 1
		 1081 1080 0 1017 1082 1 1082 1081 1 1082 1083 1 1083 1081 1 1082 1084 1 1084 1083 1
		 1084 1085 1 1085 1083 1 1084 1086 1 1086 1085 1 1087 1085 1 1086 1087 1 1086 1088 1
		 1088 1087 0 1086 1089 1 1089 1088 1 1089 514 1 514 1088 0 1086 507 1 507 1089 1 1086 1090 1
		 1090 507 1 1013 507 1 1090 1013 1 1090 1091 1 1091 1013 1 1090 1084 1 1084 1091 1
		 1087 1092 0 1092 1085 1 1092 1083 1 1092 1093 0 1093 1083 1 1094 1083 1 1093 1094 1
		 1095 1094 0 1093 1095 0 1082 1091 1 1094 1081 0 1017 1091 1 1014 1091 1 1010 507 1
		 968 1002 1 999 1006 1 1002 969 1 969 1000 1 1001 995 1 1096 995 1 1001 1096 1 1001 973 1
		 973 1096 1 994 1011 1 1097 1011 1 994 1097 1 1097 509 1 509 1011 1 536 509 1 1097 536 1
		 1096 993 1;
	setAttr ".ed[2822:2987]" 1096 1098 1 1098 993 1 1096 975 1 975 1098 1 992 1097 1
		 538 1097 1 992 538 1 1098 991 1 1098 1099 1 1099 991 1 1098 977 1 977 1099 1 990 538 1
		 1099 989 1 1099 981 1 981 989 1 988 539 1 539 990 1 981 987 1 551 986 1 984 551 1
		 551 545 1 545 986 1 980 949 1 949 983 1 1099 979 1 976 954 1 954 978 1 974 956 1
		 956 976 1 972 958 1 958 974 1 970 960 1 960 972 1 963 900 1 900 961 1 900 1100 1
		 1100 961 1 1100 959 1 1100 1101 1 1101 959 1 1100 904 1 904 1101 1 1101 957 1 1101 1102 1
		 1102 957 1 1101 906 1 906 1102 1 1102 955 1 1102 1103 1 1103 955 1 1102 908 1 908 1103 1
		 1103 953 1 1103 915 1 915 953 1 1103 910 1 910 915 1 952 978 1 558 946 1 945 558 1
		 945 563 1 563 558 1 945 941 1 941 563 1 948 919 1 564 941 1 940 564 1 940 569 1 569 564 1
		 940 936 1 936 569 1 943 938 1 943 920 1 920 938 1 920 923 1 923 938 1 570 936 1 934 570 1
		 572 934 1 933 572 1 935 926 1 924 931 1 922 931 1 922 841 1 841 931 1 909 853 1 853 911 1
		 907 854 1 854 909 1 1104 854 1 907 1104 1 905 1104 1 1105 1104 1 905 1105 1 1105 857 1
		 857 1104 1 903 1105 1 1106 1105 1 903 1106 1 1106 859 1 859 1105 1 1100 901 1 902 1106 1
		 866 1106 1 902 866 1 866 861 1 861 1106 1 867 902 1 899 867 1 963 897 1 898 867 1
		 1107 898 1 895 1107 1 1107 868 1 868 898 1 893 1107 1 1108 1107 1 893 1108 1 1108 870 1
		 870 1107 1 1108 1109 1 1109 870 1 1108 1110 1 1110 1109 1 1111 1109 1 1110 1111 1
		 887 1111 1 1110 887 1 1111 874 1 874 1109 1 1111 883 1 883 874 1 1108 890 1 890 1110 1
		 1030 892 1 884 1111 1 1051 882 1 875 883 1 775 876 1 871 1109 1 779 872 1 862 787 1
		 787 860 1 783 787 1 862 783 1 860 788 1 788 858 1 858 790 1 790 856 1 855 1104 1
		 851 911 1 849 911 1 850 845 1 850 799 1 799 845 1 799 805 1 805 845 1 840 809 1 809 838 1
		 835 929 1 829 933 1 829 1112 1 1112 933 1 574 933 1 1112 574 1;
	setAttr ".ed[2988:3153]" 1112 578 1 578 574 1 1112 827 1 827 578 1 834 828 1
		 834 1113 1 1113 828 1 834 819 1 819 1113 1 1113 824 1 1113 821 1 822 826 1 592 826 1
		 822 592 1 592 586 1 586 826 1 820 596 1 596 822 1 820 1114 1 1114 596 1 818 1114 1
		 818 1115 1 1115 1114 1 599 1114 1 1115 599 1 815 1115 1 836 813 1 814 1115 1 814 601 1
		 601 1115 1 805 800 1 856 792 1 789 642 1 642 791 1 1116 784 1 781 1116 1 1116 752 1
		 752 784 1 778 1116 1 876 776 1 777 1116 1 777 754 1 754 1116 1 774 756 1 756 777 1
		 771 756 1 765 1117 0 1117 764 1 1117 735 1 735 764 1 737 760 1 759 753 1 759 748 1
		 748 753 1 736 731 1 1117 734 0 733 1118 0 1118 730 1 1118 729 0 703 743 1 717 706 1
		 706 720 1 726 718 0 714 708 1 714 707 1 714 693 1 693 707 1 704 720 1 699 657 1 696 667 1
		 667 698 1 694 669 1 669 696 1 692 671 1 671 694 1 690 673 1 673 692 1 688 675 1 675 690 1
		 688 683 1 683 675 1 715 687 0 686 1119 0 1119 685 1 1119 1120 1 1120 685 1 1121 685 1
		 1120 1121 1 1120 1122 1 1122 1121 1 1120 1123 1 1123 1122 1 1123 1124 1 1124 1122 1
		 1123 1125 1 1125 1124 1 1125 1126 1 1126 1124 1 1127 1126 1 1125 1127 1 1128 1127 1
		 1125 1128 1 1125 1129 1 1129 1128 0 1128 1130 0 1130 1127 1 1130 1131 1 1131 1127 1
		 1131 1132 0 1132 1127 1 1130 1133 0 1133 1131 0 1132 1126 1 1134 1126 1 1132 1134 0
		 1134 1135 1 1135 1126 1 1134 1136 0 1136 1135 1 1136 1137 1 1137 1135 1 1138 1135 1
		 1137 1138 1 1137 1139 1 1139 1138 1 1140 1138 1 1139 1140 1 1139 1141 1 1141 1140 1
		 1141 1142 1 1142 1140 1 1141 1143 1 1143 1142 1 1143 1144 1 1144 1142 1 1143 1145 1
		 1145 1144 1 1145 1146 1 1146 1144 1 1145 1147 1 1147 1146 1 1147 1148 1 1148 1146 1
		 1149 1148 1 1147 1149 1 1150 1149 1 1147 1150 1 1147 1151 1 1151 1150 1 1151 1152 1
		 1152 1150 1 1152 621 1 621 1150 1 1153 621 1 1152 1153 1 1152 1154 1 1154 1153 1
		 1154 1155 1 1155 1153 1 1155 1156 1 1156 1153 1 1156 620 1 620 1153 1 1156 1157 1
		 1157 620 1 1156 1158 1;
	setAttr ".ed[3154:3319]" 1158 1157 1 1158 1159 1 1159 1157 1 1159 1160 1 1160 1157 1
		 618 1157 1 1160 618 1 1159 1161 1 1161 1160 1 1161 614 1 614 1160 1 1162 614 1 1161 1162 1
		 1163 1162 1 1161 1163 1 1163 1164 1 1164 1162 1 1164 1165 1 1165 1162 1 1165 612 1
		 612 1162 1 1164 1166 1 1166 1165 1 1166 606 1 606 1165 1 1164 1167 1 1167 1166 1
		 1168 1166 1 1167 1168 1 1169 1168 1 1167 1169 1 1170 1169 1 1167 1170 1 1167 1171 1
		 1171 1170 1 1172 1170 1 1171 1172 1 1171 1173 1 1173 1172 1 1171 1163 1 1163 1173 1
		 1159 1173 1 1163 1159 1 1174 1172 1 1173 1174 1 1158 1174 1 1173 1158 1 1158 1175 1
		 1175 1174 1 1176 1174 1 1175 1176 1 1177 1176 1 1175 1177 1 1155 1177 1 1175 1155 1
		 1155 1178 1 1178 1177 1 1179 1178 1 1155 1179 1 1180 1178 1 1179 1180 1 1181 1180 1
		 1179 1181 1 1179 1182 1 1182 1181 1 1182 1183 1 1183 1181 1 1183 1184 1 1184 1181 1
		 1185 1181 1 1184 1185 1 1184 1186 1 1186 1185 1 1187 1185 1 1186 1187 0 1187 1188 1
		 1188 1185 1 1189 1188 1 1187 1189 0 1189 1190 1 1190 1188 1 1190 1191 1 1191 1188 1
		 1191 1180 1 1180 1188 1 1190 1192 1 1192 1191 1 1193 1192 1 1190 1193 1 1194 1193 1
		 1190 1194 1 1195 1193 1 1194 1195 0 1195 1196 1 1196 1193 1 1197 1196 1 1195 1197 0
		 1197 1198 1 1198 1196 1 1198 1199 1 1199 1196 1 1199 1200 1 1200 1196 1 1199 1176 1
		 1176 1200 1 1199 1201 1 1201 1176 1 1199 1202 1 1202 1201 1 1202 1203 1 1203 1201 1
		 1203 1172 1 1172 1201 1 1202 1204 1 1204 1203 1 1204 1205 1 1205 1203 1 1205 1170 1
		 1170 1203 1 1204 1206 1 1206 1205 1 1206 1207 1 1207 1205 1 1207 1169 1 1169 1205 1
		 1207 1208 1 1208 1169 1 1209 1208 1 1207 1209 1 1210 1209 1 1207 1210 1 1210 1211 1
		 1211 1209 1 598 1209 1 1211 598 1 1210 1212 1 1212 1211 1 1212 594 1 594 1211 1 1212 1213 1
		 1213 594 1 1213 590 0 590 594 1 1212 1214 1 1214 1213 0 1215 1214 1 1212 1215 1 1215 1216 1
		 1216 1214 0 1215 1217 1 1217 1216 1 1218 1216 0 1217 1218 1 1217 1219 1 1219 1218 1
		 1220 1218 0 1219 1220 1 1219 1198 1 1198 1220 1 1219 1202 1 1202 1198 1 1217 1204 1
		 1204 1219 1 1215 1206 1 1206 1217 1 1215 1210 1;
	setAttr ".ed[3320:3485]" 1210 1206 1 1209 600 1 600 1208 1 1197 1220 0 1200 1193 1
		 1200 1192 1 1200 1177 1 1177 1192 1 1192 1178 1 1178 1191 1 1189 1194 0 1180 1185 1
		 1184 1221 1 1221 1186 0 1222 1221 1 1184 1222 1 1222 1223 1 1223 1221 0 1224 1223 1
		 1222 1224 1 1183 1224 1 1222 1183 1 1183 1225 1 1225 1224 1 1226 1225 1 1183 1226 1
		 1226 1141 1 1141 1225 1 1225 1227 1 1227 1224 1 1228 1224 1 1227 1228 1 1229 1228 0
		 1227 1229 1 1137 1229 1 1227 1137 1 1225 1139 1 1139 1227 1 1228 1223 0 1182 1226 1
		 1230 1226 1 1182 1230 1 1182 1154 1 1154 1230 1 1230 1231 1 1231 1226 1 1230 1151 1
		 1151 1231 1 1145 1231 1 1151 1145 1 1143 1226 1 1231 1143 1 1179 1154 1 1201 1174 1
		 1208 1168 1 1208 602 1 602 1168 1 1168 604 1 604 1166 1 1164 1171 1 1156 1175 1 1152 1230 1
		 1150 622 1 622 1149 1 1232 1148 1 1149 1232 1 1149 624 1 624 1232 1 1233 1232 1 624 1233 1
		 1233 1234 1 1234 1232 1 1235 1234 1 1233 1235 1 1233 1236 1 1236 1235 1 1237 1235 1
		 1236 1237 1 1236 1238 1 1238 1237 1 1239 1237 1 1238 1239 1 1238 635 1 635 1239 1
		 640 1239 1 635 640 1 640 663 1 663 1239 1 1239 664 1 664 1237 1 1236 627 1 627 1238 1
		 627 634 1 634 1238 1 1237 666 1 666 1235 1 1233 625 1 625 1236 1 1235 668 1 668 1234 1
		 1234 1240 1 1240 1232 1 1234 670 1 670 1240 1 1240 1148 1 1240 1241 1 1241 1148 1
		 1240 672 1 672 1241 1 1241 1146 1 1241 677 1 677 1146 1 677 1144 1 678 1142 1 1144 678 1
		 680 1140 1 1142 680 1 680 1242 1 1242 1140 1 1242 1138 1 1242 1243 1 1243 1138 1
		 1242 1244 1 1244 1243 1 1242 681 1 681 1244 1 1121 1244 1 681 1121 1 1122 1243 1
		 1244 1122 1 1243 1135 1 1124 1135 1 1243 1124 1 1136 1229 0 1123 1129 1 1123 1245 1
		 1245 1129 0 1120 1245 1 1119 1245 0 1121 682 1 676 683 1 1241 674 1 665 698 1 659 698 1
		 665 659 1 639 791 1 629 801 1 629 611 1 611 801 1 634 628 1 623 617 1 617 626 1 1160 616 1
		 613 629 1 1165 609 1 608 803 1 597 1114 1 1211 595 1 593 822 1 589 1246 0 1246 587 1
		 1247 587 1 1246 1247 1 1248 1247 1 1246 1248 0 1248 1249 1;
	setAttr ".ed[3486:3651]" 1249 1247 1 1250 1247 1 1249 1250 1 1251 1250 1 1249 1251 1
		 1252 1251 0 1249 1252 1 1249 1253 1 1253 1252 1 1254 1252 0 1253 1254 0 1251 1255 0
		 1255 1250 1 1255 583 1 583 1250 1 1250 585 1 585 1247 1 1248 1253 0 580 825 1 1255 582 0
		 581 576 0 576 1256 0 1256 573 1 1256 571 1 1256 1257 0 1257 571 1 1257 568 1 1257 567 0
		 566 561 0 560 555 0 554 549 0 548 1258 0 1258 546 1 1258 1259 1 1259 546 1 1258 1260 0
		 1260 1259 1 1260 526 1 526 1259 1 542 1259 1 526 542 1 1259 543 1 541 988 1 542 527 1
		 527 540 1 540 529 1 529 537 1 528 533 1 522 533 1 528 522 1 1260 525 0 518 533 1
		 513 534 1 519 515 0 1089 512 1 1089 506 1 1261 1262 1 1262 1263 1 1263 1261 1 1262 1264 1
		 1264 1263 1 1264 1265 1 1265 1263 1 1264 1266 1 1266 1265 1 1266 1267 1 1267 1265 1
		 1268 1265 1 1267 1268 1 1269 1268 1 1267 1269 1 1267 1270 1 1270 1269 1 1270 1271 1
		 1271 1269 1 1271 1272 1 1272 1269 1 1271 1273 1 1273 1272 1 1274 1273 1 1271 1274 1
		 1271 1275 1 1275 1274 1 1276 1274 1 1275 1276 1 1277 1276 1 1275 1277 1 1275 1278 1
		 1278 1277 1 1279 1277 1 1278 1279 1 1278 1280 1 1280 1279 1 1281 1279 1 1280 1281 1
		 1280 1282 1 1282 1281 0 1280 1283 1 1283 1282 1 1284 1283 1 1280 1284 1 1284 1285 1
		 1285 1283 1 1284 1270 1 1270 1285 1 1284 1286 1 1286 1270 1 1284 1278 1 1278 1286 1
		 1287 1283 1 1285 1287 1 1285 1266 1 1266 1287 1 1288 1287 1 1266 1288 1 1289 1287 1
		 1288 1289 1 1288 1290 1 1290 1289 0 1288 1291 1 1291 1290 1 1264 1291 1 1288 1264 1
		 1264 1292 1 1292 1291 1 1293 1291 1 1292 1293 1 1292 1294 1 1294 1293 1 1294 1295 1
		 1295 1293 1 1295 1296 1 1296 1293 1 1296 1297 1 1297 1293 1 1297 1298 1 1298 1293 1
		 1297 1299 1 1299 1298 1 1299 1290 0 1290 1298 1 1300 1299 0 1297 1300 1 1297 1301 1
		 1301 1300 0 1296 1301 1 1302 1301 1 1296 1302 1 1302 1303 1 1303 1301 0 1304 1303 1
		 1302 1304 1 1305 1304 1 1302 1305 1 1302 1295 1 1295 1305 1 1295 1306 1 1306 1305 1
		 1307 1306 1 1295 1307 1 1307 1308 1 1308 1306 1 1308 1309 1 1309 1306 1 1308 1310 1
		 1310 1309 1;
	setAttr ".ed[3652:3817]" 1308 1311 1 1311 1310 1 1311 1312 1 1312 1310 1 1313 1310 1
		 1312 1313 1 1312 1314 1 1314 1313 1 1315 1313 1 1314 1315 1 1314 1316 1 1316 1315 1
		 1316 1317 1 1317 1315 1 1317 1318 1 1318 1315 1 1318 1319 1 1319 1315 1 1320 1319 1
		 1318 1320 1 1321 1320 1 1318 1321 1 1318 1322 1 1322 1321 0 1321 1323 0 1323 1320 1
		 1323 1324 1 1324 1320 1 1324 1325 1 1325 1320 1 1324 1305 1 1305 1325 1 1305 1309 1
		 1309 1325 1 1309 1319 1 1319 1325 1 1309 1313 1 1313 1319 1 1323 1326 0 1326 1324 1
		 1326 1304 1 1304 1324 1 1326 1327 0 1327 1304 1 1317 1322 1 1317 1328 1 1328 1322 0
		 1317 1329 1 1329 1328 1 1329 1330 1 1330 1328 0 1329 1331 1 1331 1330 1 1332 1331 1
		 1329 1332 1 1329 1316 1 1316 1332 1 1333 1332 1 1316 1333 1 1333 1334 1 1334 1332 1
		 1335 1334 1 1333 1335 1 1333 1336 1 1336 1335 1 1337 1335 1 1336 1337 1 1336 1338 1
		 1338 1337 1 1339 1337 1 1338 1339 1 1338 1340 1 1340 1339 1 1340 1341 1 1341 1339 1
		 1341 1342 1 1342 1339 1 1343 1342 1 1341 1343 1 1341 1344 1 1344 1343 1 1345 1343 1
		 1344 1345 1 1346 1345 1 1344 1346 1 1347 1346 1 1344 1347 1 1348 1347 1 1344 1348 1
		 1348 1349 1 1349 1347 1 1349 1350 1 1350 1347 1 1350 1272 1 1272 1347 1 1351 1350 1
		 1349 1351 1 1349 1352 1 1352 1351 1 1307 1351 1 1352 1307 1 1353 1307 1 1352 1353 1
		 1352 1354 1 1354 1353 1 1354 1340 1 1340 1353 1 1311 1353 1 1340 1311 1 1294 1351 1
		 1307 1294 1 1294 1262 1 1262 1351 1 1349 1354 1 1261 1350 1 1351 1261 1 1261 1268 1
		 1268 1350 1 1348 1354 1 1341 1354 1 1348 1341 1 1347 1273 1 1273 1346 1 1355 1346 1
		 1273 1355 1 1273 1356 1 1356 1355 1 1356 1357 1 1357 1355 1 1345 1355 1 1357 1345 1
		 1357 1358 1 1358 1345 1 1357 1359 1 1359 1358 1 1357 1360 1 1360 1359 1 1360 1361 1
		 1361 1359 1 1362 1359 1 1361 1362 1 1363 1362 1 1361 1363 1 1361 1364 1 1364 1363 1
		 1364 1365 1 1365 1363 1 1364 1366 1 1366 1365 1 1367 1365 1 1366 1367 1 1368 1367 1
		 1366 1368 1 1366 1369 1 1369 1368 1 1369 1370 1 1370 1368 1 1371 1368 1 1370 1371 1
		 1372 1371 1 1370 1372 1 1370 1373 1 1373 1372 1 1374 1372 1 1373 1374 1 1373 1375 1;
	setAttr ".ed[3818:3983]" 1375 1374 1 1376 1374 1 1375 1376 1 1375 1377 1 1377 1376 0
		 1375 1378 1 1378 1377 1 1379 1378 1 1375 1379 1 1379 1380 1 1380 1378 1 1380 1381 1
		 1381 1378 1 1382 1378 1 1381 1382 1 1381 1383 1 1383 1382 0 1381 1384 1 1384 1383 1
		 1385 1384 1 1381 1385 1 1385 1277 1 1277 1384 1 1384 1386 1 1386 1383 0 1384 1279 1
		 1279 1386 1 1380 1385 1 1387 1385 1 1380 1387 1 1380 1388 1 1388 1387 1 1388 1389 1
		 1389 1387 1 1390 1387 1 1389 1390 1 1389 1391 1 1391 1390 1 1389 1392 1 1392 1391 1
		 1389 1393 1 1393 1392 1 1393 1394 1 1394 1392 1 1394 1360 1 1360 1392 1 1394 1395 1
		 1395 1360 1 1396 1395 1 1394 1396 1 1394 1369 1 1369 1396 1 1396 1364 1 1364 1395 1
		 1393 1369 1 1393 1397 1 1397 1369 1 1393 1388 1 1388 1397 1 1379 1397 1 1388 1379 1
		 1379 1373 1 1373 1397 1 1392 1357 1 1357 1391 1 1356 1390 1 1391 1356 1 1274 1390 1
		 1356 1274 1 1390 1276 1 1276 1387 1 1276 1385 1 1382 1377 0 1376 1398 0 1398 1374 1
		 1398 1399 1 1399 1374 1 1398 1400 0 1400 1399 1 1400 1401 1 1401 1399 1 1402 1399 1
		 1401 1402 1 1401 1403 1 1403 1402 1 1404 1402 1 1403 1404 1 1403 1405 1 1405 1404 1
		 1405 1406 1 1406 1404 1 1407 1404 1 1406 1407 1 1367 1407 1 1406 1367 1 1406 1408 1
		 1408 1367 1 1408 1409 1 1409 1367 1 1408 1410 1 1410 1409 1 1411 1409 1 1410 1411 1
		 1410 1412 1 1412 1411 1 1410 1413 1 1413 1412 1 1410 1414 1 1414 1413 1 1415 1413 1
		 1414 1415 1 1414 1416 1 1416 1415 1 1416 1417 1 1417 1415 1 1417 1418 1 1418 1415 1
		 1418 1419 1 1419 1415 1 1418 1420 1 1420 1419 1 1420 1421 1 1421 1419 1 1422 1419 1
		 1421 1422 1 1423 1422 1 1421 1423 1 1421 1424 1 1424 1423 1 1424 1425 1 1425 1423 1
		 1424 1426 1 1426 1425 1 1426 1427 1 1427 1425 1 1428 1425 1 1427 1428 1 1429 1428 1
		 1427 1429 1 1427 1430 1 1430 1429 1 1430 1431 1 1431 1429 1 1432 1429 1 1431 1432 1
		 1431 1433 1 1433 1432 1 1433 1434 1 1434 1432 1 1434 1435 1 1435 1432 1 1434 1436 1
		 1436 1435 1 1437 1435 1 1436 1437 1 1438 1437 1 1436 1438 1 1436 1439 1 1439 1438 1
		 1440 1439 1 1436 1440 1 1440 1441 1 1441 1439 1 1442 1439 1 1441 1442 1 1441 1443 1;
	setAttr ".ed[3984:4149]" 1443 1442 1 1443 1444 1 1444 1442 1 1444 1445 1 1445 1442 1
		 1444 1446 1 1446 1445 1 1447 1446 1 1444 1447 1 1444 1448 1 1448 1447 1 1449 1447 1
		 1448 1449 1 1448 1450 1 1450 1449 1 1450 1451 1 1451 1449 1 1451 1452 1 1452 1449 1
		 1452 1453 1 1453 1449 1 1452 1454 1 1454 1453 1 1455 1454 1 1452 1455 1 1456 1455 1
		 1452 1456 1 1456 1457 1 1457 1455 1 1456 1458 1 1458 1457 1 1459 1457 1 1458 1459 1
		 1458 1460 1 1460 1459 1 1460 1461 1 1461 1459 1 1462 1459 1 1461 1462 1 1463 1462 1
		 1461 1463 1 1461 1464 1 1464 1463 1 1465 1463 1 1464 1465 1 1464 1466 1 1466 1465 1
		 1467 1465 1 1466 1467 1 1466 1468 1 1468 1467 1 1469 1467 1 1468 1469 1 1468 1470 1
		 1470 1469 1 1471 1469 1 1470 1471 1 1470 1472 1 1472 1471 1 1473 1471 1 1472 1473 1
		 1472 1474 1 1474 1473 1 1475 1473 1 1474 1475 1 1476 1475 1 1474 1476 1 1474 1477 1
		 1477 1476 1 1478 1476 1 1477 1478 1 1479 1478 1 1477 1479 1 1477 1480 1 1480 1479 1
		 1480 1481 1 1481 1479 1 1482 1479 1 1481 1482 1 1481 1483 1 1483 1482 1 1484 1482 1
		 1483 1484 1 1483 1485 1 1485 1484 0 1483 1486 1 1486 1485 1 1487 1486 1 1483 1487 1
		 1488 1486 1 1487 1488 1 1489 1488 1 1487 1489 1 1490 1489 1 1487 1490 1 1487 1481 1
		 1481 1490 1 1491 1489 1 1490 1491 1 1490 1492 1 1492 1491 1 1492 1493 1 1493 1491 1
		 1494 1491 1 1493 1494 1 1495 1494 1 1493 1495 1 1496 1495 1 1493 1496 1 1496 1470 1
		 1470 1495 1 1495 1497 1 1497 1494 1 1495 1498 1 1498 1497 1 1498 1499 1 1499 1497 1
		 1499 1500 1 1500 1497 1 1501 1500 1 1499 1501 1 1499 1502 1 1502 1501 1 1502 1503 1
		 1503 1501 1 1503 1504 1 1504 1501 1 1503 1505 1 1505 1504 1 1506 1504 1 1505 1506 1
		 1505 1507 1 1507 1506 1 1507 1508 1 1508 1506 1 1507 1509 1 1509 1508 1 1510 1508 1
		 1509 1510 1 1509 1511 1 1511 1510 1 1512 1510 1 1511 1512 1 1511 1513 1 1513 1512 1
		 1513 1514 1 1514 1512 1 1515 1514 1 1513 1515 1 1513 1516 1 1516 1515 1 1517 1515 1
		 1516 1517 1 1518 1517 1 1516 1518 1 1519 1518 1 1516 1519 1 1520 1518 1 1519 1520 1
		 1519 1521 1 1521 1520 1 1521 1522 1 1522 1520 1 1522 1523 1 1523 1520 1 1523 1524 1;
	setAttr ".ed[4150:4315]" 1524 1520 1 1523 1525 1 1525 1524 1 1525 1526 1 1526 1524 1
		 1526 1527 1 1527 1524 1 1528 1527 1 1526 1528 1 1526 1529 1 1529 1528 1 1530 1528 1
		 1529 1530 1 1529 1531 1 1531 1530 1 1532 1530 1 1531 1532 1 1531 1533 1 1533 1532 1
		 1533 1534 1 1534 1532 1 1534 1535 1 1535 1532 1 1534 1536 1 1536 1535 1 1534 1537 1
		 1537 1536 1 1537 1538 1 1538 1536 1 1537 1539 1 1539 1538 1 1539 1540 1 1540 1538 1
		 1539 1541 1 1541 1540 1 1541 1542 1 1542 1540 1 1543 1540 1 1542 1543 1 1542 1544 1
		 1544 1543 1 1545 1543 1 1544 1545 1 1544 1546 1 1546 1545 1 1547 1546 0 1544 1547 1
		 1544 1548 1 1548 1547 1 1549 1547 0 1548 1549 1 1548 1550 1 1550 1549 1 1551 1549 0
		 1550 1551 1 1550 1552 1 1552 1551 1 1553 1551 0 1552 1553 1 1552 1554 1 1554 1553 1
		 1555 1553 0 1554 1555 1 1554 1556 1 1556 1555 1 1557 1555 0 1556 1557 1 1556 1558 1
		 1558 1557 1 1559 1557 0 1558 1559 1 1558 1560 1 1560 1559 1 1558 1561 1 1561 1560 1
		 1562 1560 1 1561 1562 1 1561 1563 1 1563 1562 1 1563 1564 1 1564 1562 1 1565 1562 1
		 1564 1565 1 1564 1566 1 1566 1565 1 1567 1565 1 1566 1567 1 1566 1568 1 1568 1567 1
		 1569 1567 1 1568 1569 1 1568 1570 1 1570 1569 1 1571 1570 1 1568 1571 1 1571 1572 1
		 1572 1570 1 1571 1573 1 1573 1572 1 1573 1574 1 1574 1572 1 1575 1572 1 1574 1575 1
		 1574 1576 1 1576 1575 1 1576 1577 1 1577 1575 1 1577 1578 0 1578 1575 1 1578 1570 1
		 1570 1575 1 1576 1579 1 1579 1577 0 1580 1579 1 1576 1580 1 1581 1580 1 1576 1581 1
		 1581 1582 1 1582 1580 1 1582 1583 1 1583 1580 1 1584 1580 1 1583 1584 1 1583 1585 1
		 1585 1584 1 1585 1586 1 1586 1584 0 1585 1587 1 1587 1586 1 1587 1588 1 1588 1586 1
		 1588 1589 1 1589 1586 0 1588 1590 1 1590 1589 1 1590 1591 1 1591 1589 0 1590 1592 1
		 1592 1591 1 1592 1593 1 1593 1591 0 1592 1594 1 1594 1593 1 1595 1593 0 1594 1595 1
		 1594 1596 1 1596 1595 1 1597 1596 1 1594 1597 1 1594 1598 1 1598 1597 1 1599 1597 1
		 1598 1599 1 1598 1600 1 1600 1599 1 1600 1601 1 1601 1599 1 1601 1602 1 1602 1599 1
		 1601 1603 1 1603 1602 0 1601 1604 1 1604 1603 1 1605 1603 0 1604 1605 1 1604 1606 1;
	setAttr ".ed[4316:4481]" 1606 1605 1 1604 1607 1 1607 1606 1 1608 1606 1 1607 1608 1
		 1607 1609 1 1609 1608 1 1610 1608 1 1609 1610 1 1609 1611 1 1611 1610 1 1609 1612 1
		 1612 1611 1 1613 1612 1 1609 1613 1 1613 1614 1 1614 1612 1 1615 1614 1 1613 1615 1
		 1613 1616 1 1616 1615 1 1617 1615 1 1616 1617 1 1604 1617 1 1616 1604 1 1617 1618 1
		 1618 1615 1 1617 1619 1 1619 1618 1 1619 1588 1 1588 1618 1 1617 1600 1 1600 1619 1
		 1600 1620 1 1620 1619 1 1590 1619 1 1620 1590 1 1618 1587 1 1587 1615 1 1613 1607 1
		 1607 1616 1 1587 1614 1 1614 1621 1 1621 1612 1 1622 1612 1 1621 1622 1 1621 1623 1
		 1623 1622 1 1621 1583 1 1583 1623 1 1624 1622 1 1623 1624 1 1623 1625 1 1625 1624 1
		 1626 1624 1 1625 1626 1 1625 1627 1 1627 1626 1 1627 1628 1 1628 1626 1 1628 1629 1
		 1629 1626 1 1628 1420 1 1420 1629 1 1420 1630 1 1630 1629 1 1630 1631 1 1631 1629 1
		 1631 1624 1 1624 1629 1 1630 1632 1 1632 1631 1 1611 1631 1 1632 1611 1 1611 1622 1
		 1622 1631 1 1633 1632 1 1630 1633 1 1418 1633 1 1630 1418 1 1633 1634 1 1634 1632 1
		 1610 1632 1 1634 1610 1 1635 1610 1 1634 1635 1 1634 1636 1 1636 1635 1 1636 1637 1
		 1637 1635 1 1638 1635 1 1637 1638 1 1639 1638 1 1637 1639 1 1640 1639 0 1637 1640 1
		 1637 1641 1 1641 1640 0 1637 1642 1 1642 1641 1 1642 1643 1 1643 1641 0 1642 1644 1
		 1644 1643 1 1642 1645 1 1645 1644 1 1645 1646 1 1646 1644 1 1647 1644 1 1646 1647 1
		 1646 1648 1 1648 1647 0 1646 1649 1 1649 1648 1 1650 1649 1 1646 1650 1 1650 1651 1
		 1651 1649 1 1651 1652 1 1652 1649 1 1653 1649 1 1652 1653 1 1652 1654 1 1654 1653 0
		 1652 1655 1 1655 1654 1 1656 1655 1 1652 1656 1 1656 1403 1 1403 1655 1 1655 1657 1
		 1657 1654 0 1655 1401 1 1401 1657 1 1651 1656 1 1658 1656 1 1651 1658 1 1658 1405 1
		 1405 1656 1 1658 1659 1 1659 1405 1 1658 1416 1 1416 1659 1 1660 1416 1 1658 1660 1
		 1658 1650 1 1650 1660 1 1650 1645 1 1645 1660 1 1645 1661 1 1661 1660 1 1645 1636 1
		 1636 1661 1 1661 1417 1 1417 1660 1 1661 1633 1 1633 1417 1 1653 1648 0 1642 1636 1
		 1647 1643 0 1639 1662 0 1662 1638 1 1662 1606 1 1606 1638 1 1638 1608 1 1608 1635 1;
	setAttr ".ed[4482:4647]" 1634 1661 1 1627 1424 1 1424 1628 1 1625 1663 1 1663 1627 1
		 1582 1663 1 1625 1582 1 1663 1426 1 1426 1627 1 1663 1664 1 1664 1426 1 1581 1664 1
		 1663 1581 1 1581 1574 1 1574 1664 1 1664 1665 1 1665 1426 1 1664 1573 1 1573 1665 1
		 1573 1666 1 1666 1665 1 1666 1430 1 1430 1665 1 1666 1667 1 1667 1430 1 1666 1668 1
		 1668 1667 1 1571 1668 1 1666 1571 1 1571 1566 1 1566 1668 1 1668 1669 1 1669 1667 1
		 1669 1670 1 1670 1667 1 1670 1431 1 1431 1667 1 1563 1670 1 1669 1563 1 1563 1671 1
		 1671 1670 1 1563 1672 1 1672 1671 1 1672 1673 1 1673 1671 1 1673 1674 1 1674 1671 1
		 1675 1671 1 1674 1675 1 1676 1675 1 1674 1676 1 1674 1677 1 1677 1676 1 1677 1678 1
		 1678 1676 1 1679 1676 1 1678 1679 1 1678 1680 1 1680 1679 1 1680 1441 1 1441 1679 1
		 1678 1681 1 1681 1680 1 1681 1682 1 1682 1680 1 1682 1443 1 1443 1680 1 1682 1683 1
		 1683 1443 1 1682 1684 1 1684 1683 1 1684 1450 1 1450 1683 1 1685 1450 1 1684 1685 1
		 1684 1686 1 1686 1685 1 1687 1685 1 1686 1687 1 1686 1688 1 1688 1687 1 1686 1689 1
		 1689 1688 1 1690 1688 1 1689 1690 1 1689 1691 1 1691 1690 1 1691 1692 1 1692 1690 1
		 1692 1693 1 1693 1690 1 1692 1694 1 1694 1693 1 1692 1695 1 1695 1694 1 1696 1694 1
		 1695 1696 1 1695 1525 1 1525 1696 1 1697 1525 1 1695 1697 1 1697 1698 1 1698 1525 1
		 1697 1699 1 1699 1698 1 1697 1700 1 1700 1699 1 1700 1701 1 1701 1699 1 1701 1531 1
		 1531 1699 1 1700 1702 1 1702 1701 1 1703 1701 1 1702 1703 1 1704 1703 1 1702 1704 1
		 1705 1704 1 1702 1705 1 1702 1691 1 1691 1705 1 1705 1706 1 1706 1704 1 1706 1681 1
		 1681 1704 1 1681 1707 1 1707 1704 1 1705 1708 1 1708 1706 1 1684 1706 1 1708 1684 1
		 1705 1689 1 1689 1708 1 1707 1703 1 1707 1709 1 1709 1703 1 1709 1533 1 1533 1703 1
		 1709 1710 1 1710 1533 1 1709 1711 1 1711 1710 1 1712 1710 1 1711 1712 1 1711 1713 1
		 1713 1712 1 1714 1712 1 1713 1714 1 1713 1715 1 1715 1714 1 1716 1714 1 1715 1716 1
		 1715 1717 1 1717 1716 1 1718 1716 1 1717 1718 1 1717 1550 1 1550 1718 1 1718 1541 1
		 1541 1716 1 1541 1719 1 1719 1716 1 1715 1720 1 1720 1717 1 1720 1552 1 1552 1717 1;
	setAttr ".ed[4648:4813]" 1721 1720 1 1715 1721 1 1721 1722 1 1722 1720 1 1722 1554 1
		 1554 1720 1 1723 1722 1 1721 1723 1 1724 1723 1 1721 1724 1 1721 1713 1 1713 1724 1
		 1673 1723 1 1724 1673 1 1725 1673 1 1724 1725 1 1724 1711 1 1711 1725 1 1723 1726 1
		 1726 1722 1 1726 1556 1 1556 1722 1 1672 1726 1 1723 1672 1 1672 1561 1 1561 1726 1
		 1719 1714 1 1537 1714 1 1719 1537 1 1537 1712 1 1712 1534 1 1534 1710 1 1709 1725 1
		 1677 1725 1 1709 1677 1 1707 1677 1 1533 1701 1 1700 1691 1 1697 1692 1 1692 1700 1
		 1699 1529 1 1529 1698 1 1727 1694 1 1696 1727 1 1728 1727 1 1696 1728 1 1523 1728 1
		 1696 1523 1 1728 1729 1 1729 1727 1 1730 1729 1 1728 1730 1 1522 1730 1 1728 1522 1
		 1522 1731 1 1731 1730 1 1505 1730 1 1731 1505 1 1505 1732 1 1732 1730 1 1732 1729 1
		 1733 1729 1 1732 1733 1 1732 1734 1 1734 1733 1 1734 1735 1 1735 1733 1 1736 1733 1
		 1735 1736 1 1737 1736 1 1735 1737 1 1735 1738 1 1738 1737 1 1738 1739 1 1739 1737 1
		 1739 1740 1 1740 1737 1 1687 1737 1 1740 1687 1 1739 1451 1 1451 1740 1 1739 1456 1
		 1456 1451 1 1685 1740 1 1451 1685 1 1738 1458 1 1458 1739 1 1741 1738 1 1735 1741 1
		 1741 1460 1 1460 1738 1 1742 1460 1 1741 1742 1 1741 1502 1 1502 1742 1 1743 1742 1
		 1502 1743 1 1743 1464 1 1464 1742 1 1741 1734 1 1734 1502 1 1687 1736 1 1687 1744 1
		 1744 1736 1 1745 1736 1 1744 1745 1 1744 1693 1 1693 1745 1 1744 1688 1 1688 1693 1
		 1745 1746 1 1746 1736 1 1745 1727 1 1727 1746 1 1746 1733 1 1732 1503 1 1503 1734 1
		 1746 1729 1 1745 1694 1 1686 1708 1 1682 1706 1 1678 1707 1 1679 1747 1 1747 1676 1
		 1440 1747 1 1679 1440 1 1440 1434 1 1434 1747 1 1674 1725 1 1747 1675 1 1747 1433 1
		 1433 1675 1 1670 1675 1 1433 1670 1 1668 1564 1 1564 1669 1 1623 1582 1 1614 1585 1
		 1585 1621 1 1662 1605 0 1601 1617 1 1598 1620 1 1598 1592 1 1592 1620 1 1602 1597 1
		 1602 1748 0 1748 1597 1 1748 1596 1 1748 1749 0 1749 1596 1 1749 1595 0 1584 1750 0
		 1750 1580 1 1750 1579 0 1578 1569 0 1569 1751 0 1751 1567 1 1751 1752 1 1752 1567 1
		 1751 1753 1 1753 1752 1 1753 1754 1 1754 1752 1 1755 1752 1 1754 1755 1 1754 1756 0;
	setAttr ".ed[4814:4979]" 1756 1755 1 1756 1560 1 1560 1755 1 1755 1565 1 1565 1752 1
		 1753 1757 1 1757 1754 0 1758 1757 0 1753 1758 1 1753 1759 1 1759 1758 1 1759 1760 1
		 1760 1758 0 1759 1761 1 1761 1760 0 1759 1762 1 1762 1761 1 1762 1763 0 1763 1761 0
		 1753 1762 1 1751 1762 0 1755 1562 1 1558 1726 1 1756 1559 0 1548 1718 1 1548 1542 1
		 1542 1718 1 1546 1764 0 1764 1545 1 1765 1545 1 1764 1765 1 1766 1765 1 1764 1766 0
		 1767 1765 1 1766 1767 1 1766 1768 0 1768 1767 1 1515 1767 1 1768 1515 1 1767 1769 1
		 1769 1765 1 1769 1770 1 1770 1765 1 1769 1771 1 1771 1770 1 1772 1770 1 1771 1772 1
		 1771 1773 1 1773 1772 1 1538 1772 1 1773 1538 1 1771 1774 1 1774 1773 1 1774 1535 1
		 1535 1773 1 1530 1535 1 1774 1530 1 1775 1774 1 1771 1775 1 1528 1774 1 1775 1528 1
		 1772 1543 1 1543 1770 1 1769 1775 1 1517 1775 1 1769 1517 1 1527 1775 1 1517 1527 1
		 1767 1517 1 1770 1545 1 1772 1540 1 1539 1719 1 1773 1536 1 1526 1698 1 1518 1524 1
		 1527 1518 1 1521 1731 1 1521 1509 1 1509 1731 1 1519 1511 1 1511 1521 1 1513 1519 1
		 1768 1514 1 1768 1776 0 1776 1514 1 1776 1777 1 1777 1514 1 1776 1778 0 1778 1777 1
		 1778 1779 1 1779 1777 1 1780 1777 1 1779 1780 1 1779 1781 1 1781 1780 1 1781 1782 1
		 1782 1780 1 1782 1510 1 1510 1780 1 1781 1783 1 1783 1782 1 1784 1782 1 1783 1784 1
		 1785 1784 1 1783 1785 1 1489 1785 1 1783 1489 1 1786 1784 1 1785 1786 1 1785 1494 1
		 1494 1786 1 1494 1500 1 1500 1786 1 1504 1786 1 1500 1504 1 1786 1506 1 1506 1784 1
		 1784 1508 1 1508 1782 1 1781 1488 1 1488 1783 1 1781 1787 1 1787 1488 1 1779 1787 1
		 1788 1787 1 1779 1788 1 1788 1789 0 1789 1787 1 1789 1486 1 1486 1787 1 1780 1512 1
		 1512 1777 1 1778 1788 0 1507 1731 1 1499 1743 1 1498 1743 1 1466 1743 1 1498 1466 1
		 1495 1468 1 1468 1498 1 1785 1491 1 1492 1496 1 1492 1790 1 1790 1496 1 1790 1472 1
		 1472 1496 1 1492 1480 1 1480 1790 1 1490 1480 1 1789 1485 0 1484 1791 0 1791 1482 1
		 1791 1792 1 1792 1482 1 1791 1793 0 1793 1792 1 1793 1794 1 1794 1792 1 1478 1792 1
		 1794 1478 1 1795 1478 1 1794 1795 1 1794 1796 1 1796 1795 1 1796 1797 1 1797 1795 1;
	setAttr ".ed[4980:5145]" 1797 1476 1 1476 1795 1 1797 1798 1 1798 1476 1 1799 1798 1
		 1797 1799 1 1797 1800 1 1800 1799 1 1800 1801 1 1801 1799 1 1802 1801 0 1800 1802 1
		 1800 1803 1 1803 1802 0 1800 1796 1 1796 1803 1 1796 1804 1 1804 1803 0 1801 1805 0
		 1805 1799 1 1805 1806 1 1806 1799 1 1805 1807 0 1807 1806 1 1807 1808 1 1808 1806 1
		 1808 1475 1 1475 1806 1 1475 1798 1 1798 1806 1 1807 1809 0 1809 1808 1 1809 1810 1
		 1810 1808 1 1810 1473 1 1473 1808 1 1810 1811 1 1811 1473 1 1810 1812 1 1812 1811 1
		 1813 1811 1 1812 1813 1 1812 1814 1 1814 1813 1 1815 1813 1 1814 1815 1 1814 1816 1
		 1816 1815 1 1817 1815 1 1816 1817 1 1816 1818 1 1818 1817 1 1819 1817 1 1818 1819 1
		 1818 1820 1 1820 1819 1 1821 1819 1 1820 1821 1 1820 1822 1 1822 1821 1 1820 1823 1
		 1823 1822 1 1823 1824 1 1824 1822 1 1823 1337 1 1337 1824 1 1825 1822 1 1824 1825 1
		 1824 1342 1 1342 1825 1 1342 1826 1 1826 1825 1 1827 1825 1 1826 1827 1 1828 1827 1
		 1826 1828 1 1343 1828 1 1826 1343 1 1343 1829 1 1829 1828 1 1829 1454 1 1454 1828 1
		 1829 1830 1 1830 1454 1 1358 1830 1 1829 1358 1 1358 1831 1 1831 1830 1 1831 1453 1
		 1453 1830 1 1831 1447 1 1447 1453 1 1831 1362 1 1362 1447 1 1828 1455 1 1455 1827 1
		 1827 1832 1 1832 1825 1 1827 1833 1 1833 1832 1 1462 1832 1 1833 1462 1 1821 1832 1
		 1462 1821 1 1457 1833 1 1827 1457 1 1832 1822 1 1834 1823 1 1820 1834 1 1834 1335 1
		 1335 1823 1 1821 1463 1 1463 1819 1 1818 1834 1 1818 1835 1 1835 1834 1 1835 1334 1
		 1334 1834 1 1836 1334 1 1835 1836 1 1835 1837 1 1837 1836 1 1837 1838 1 1838 1836 1
		 1838 1331 1 1331 1836 1 1839 1331 1 1838 1839 1 1838 1840 1 1840 1839 1 1840 1841 1
		 1841 1839 0 1840 1842 1 1842 1841 0 1840 1843 1 1843 1842 1 1844 1843 1 1840 1844 1
		 1844 1812 1 1812 1843 1 1843 1810 1 1810 1842 1 1838 1844 1 1837 1844 1 1814 1844 1
		 1837 1814 1 1835 1816 1 1816 1837 1 1819 1465 1 1465 1817 1 1817 1467 1 1467 1815 1
		 1815 1469 1 1469 1813 1 1813 1471 1 1471 1811 1 1809 1842 0 1794 1804 1 1793 1804 0
		 1792 1479 1 1477 1790 1 1474 1790 1 1461 1742 1 1833 1459 1 1448 1683 1 1444 1683 1;
	setAttr ".ed[5146:5230]" 1362 1446 1 1362 1845 1 1845 1446 1 1846 1446 1 1845 1846 1
		 1845 1847 1 1847 1846 1 1411 1846 1 1847 1411 1 1411 1848 1 1848 1846 1 1848 1445 1
		 1445 1846 1 1848 1438 1 1438 1445 1 1849 1438 1 1848 1849 1 1411 1849 1 1845 1363 1
		 1363 1847 1 1445 1439 1 1849 1437 1 1849 1850 1 1850 1437 1 1849 1851 1 1851 1850 1
		 1851 1852 1 1852 1850 1 1852 1435 1 1435 1850 1 1852 1428 1 1428 1435 1 1851 1423 1
		 1423 1852 1 1412 1851 1 1849 1412 1 1412 1422 1 1422 1851 1 1428 1432 1 1427 1665 1
		 1852 1425 1 1421 1628 1 1422 1413 1 1413 1419 1 1414 1659 1 1408 1659 1 1414 1408 1
		 1847 1409 1 1847 1365 1 1365 1409 1 1406 1659 1 1407 1371 1 1371 1404 1 1371 1402 1
		 1402 1372 1 1372 1399 1 1400 1657 0 1370 1397 1 1407 1368 1 1366 1396 1 1361 1395 1
		 1831 1359 1 1829 1345 1 1824 1339 1 1338 1311 1 1312 1338 1 1336 1312 1 1333 1314 1
		 1314 1336 1 1836 1332 1 1839 1330 0 1308 1353 1 1327 1303 0 1292 1262 1 1298 1291 1
		 1289 1853 0 1853 1287 1 1853 1283 1 1853 1282 0 1281 1386 0 1275 1286 1 1271 1286 1
		 1350 1269 1 1267 1285 1 1261 1265 1;
	setAttr -s 1854 ".n";
	setAttr ".n[0:165]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr ".n[166:331]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr ".n[332:497]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr ".n[498:663]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr ".n[664:829]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr ".n[830:995]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr ".n[996:1161]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr ".n[1162:1327]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr ".n[1328:1493]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr ".n[1494:1659]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr ".n[1660:1825]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr ".n[1826:1853]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20;
	setAttr -s 3381 -ch 10143 ".fc";
	setAttr ".fc[0:499]" -type "polyFaces" 
		f 3 0 1 2
		mu 0 3 0 1 2
		f 3 3 4 -3
		mu 0 3 2 3 0
		f 3 5 6 -5
		mu 0 3 3 4 0
		f 3 7 8 -7
		mu 0 3 4 5 0
		f 3 9 10 -8
		mu 0 3 4 6 5
		f 3 11 12 -11
		mu 0 3 6 7 5
		f 3 13 -13 14
		mu 0 3 1 5 7
		f 3 -15 15 16
		mu 0 3 1 7 8
		f 3 17 18 -17
		mu 0 3 8 9 1
		f 3 19 20 -18
		mu 0 3 8 10 9
		f 3 21 22 -21
		mu 0 3 10 11 9
		f 3 23 -23 24
		mu 0 3 2 9 11
		f 3 25 26 -25
		mu 0 3 11 12 2
		f 3 -26 27 28
		mu 0 3 12 11 13
		f 3 29 30 -29
		mu 0 3 13 14 12
		f 3 31 32 -31
		mu 0 3 14 3 12
		f 3 -32 33 34
		mu 0 3 3 14 15
		f 3 35 -34 36
		mu 0 3 16 15 14
		f 3 37 -37 38
		mu 0 3 17 16 14
		f 3 -38 39 40
		mu 0 3 16 17 18
		f 3 41 42 -41
		mu 0 3 18 19 16
		f 3 43 44 -43
		mu 0 3 19 20 16
		f 3 -44 45 46
		mu 0 3 20 19 21
		f 3 47 -46 48
		mu 0 3 22 21 19
		f 3 -49 49 50
		mu 0 3 22 19 23
		f 3 -51 51 52
		mu 0 3 22 23 24
		f 3 -52 53 54
		mu 0 3 24 23 25
		f 3 55 56 -54
		mu 0 3 23 26 25
		f 3 -57 57 58
		mu 0 3 25 26 27
		f 3 59 -58 60
		mu 0 3 28 27 26
		f 3 61 -61 62
		mu 0 3 29 28 26
		f 3 -62 63 64
		mu 0 3 28 29 18
		f 3 65 66 -65
		mu 0 3 18 30 28
		f 3 67 -67 68
		mu 0 3 31 28 30
		f 3 69 70 -69
		mu 0 3 30 32 31
		f 3 71 72 -71
		mu 0 3 32 33 31
		f 3 73 -73 74
		mu 0 3 34 31 33
		f 3 -75 75 76
		mu 0 3 34 33 35
		f 3 77 78 -76
		mu 0 3 33 36 35
		f 3 79 -79 80
		mu 0 3 37 35 36
		f 3 81 82 -81
		mu 0 3 36 38 37
		f 3 -83 83 84
		mu 0 3 37 38 39
		f 3 85 86 -84
		mu 0 3 38 40 39
		f 3 87 88 -87
		mu 0 3 40 41 39
		f 3 89 90 -89
		mu 0 3 41 42 39
		f 3 91 92 -91
		mu 0 3 42 43 39
		f 3 -92 93 94
		mu 0 3 43 42 44
		f 3 95 96 -95
		mu 0 3 44 45 43
		f 3 97 -97 98
		mu 0 3 46 43 45
		f 3 99 -99 100
		mu 0 3 47 46 45
		f 3 -101 101 102
		mu 0 3 47 45 48
		f 3 103 104 -103
		mu 0 3 48 49 47
		f 3 105 -105 106
		mu 0 3 50 47 49
		f 3 107 -107 108
		mu 0 3 51 50 49
		f 3 -109 109 110
		mu 0 3 51 49 52
		f 3 111 -111 112
		mu 0 3 53 51 52
		f 3 113 -113 114
		mu 0 3 54 53 52
		f 3 115 116 -115
		mu 0 3 52 55 54
		f 3 -117 117 118
		mu 0 3 54 55 56
		f 3 119 120 -118
		mu 0 3 55 57 56
		f 3 -120 121 122
		mu 0 3 57 55 48
		f 3 123 124 -123
		mu 0 3 48 58 57
		f 3 125 126 -119
		mu 0 3 56 59 54
		f 3 127 128 -127
		mu 0 3 59 60 54
		f 3 -128 129 130
		mu 0 3 60 59 61
		f 3 131 -131 132
		mu 0 3 62 60 61
		f 3 -133 133 134
		mu 0 3 62 61 63
		f 3 135 136 -135
		mu 0 3 63 64 62
		f 3 137 138 -137
		mu 0 3 64 65 62
		f 3 139 -139 140
		mu 0 3 53 62 65
		f 3 141 142 -141
		mu 0 3 65 66 53
		f 3 -142 143 144
		mu 0 3 66 65 67
		f 3 -144 145 146
		mu 0 3 67 65 68
		f 3 147 -147 148
		mu 0 3 69 67 68
		f 3 149 -149 150
		mu 0 3 70 69 68
		f 3 -151 151 152
		mu 0 3 70 68 71
		f 3 153 154 -152
		mu 0 3 68 64 71
		f 3 155 -155 156
		mu 0 3 72 71 64
		f 3 -156 157 158
		mu 0 3 71 72 73
		f 3 -159 159 160
		mu 0 3 71 73 74
		f 3 -160 161 162
		mu 0 3 74 73 75
		f 3 163 164 -163
		mu 0 3 75 76 74
		f 3 165 -165 166
		mu 0 3 77 74 76
		f 3 167 168 -167
		mu 0 3 76 78 77
		f 3 169 -169 170
		mu 0 3 79 77 78
		f 3 171 172 -171
		mu 0 3 78 80 79
		f 3 173 174 -173
		mu 0 3 80 81 79
		f 3 175 -175 176
		mu 0 3 82 79 81
		f 3 177 178 -177
		mu 0 3 81 83 82
		f 3 179 -179 180
		mu 0 3 84 82 83
		f 3 181 -181 182
		mu 0 3 85 84 83
		f 3 183 -183 184
		mu 0 3 86 85 83
		f 3 185 -185 186
		mu 0 3 87 86 83
		f 3 -186 187 188
		mu 0 3 86 87 88
		f 3 189 -188 190
		mu 0 3 89 88 87
		f 3 -191 191 192
		mu 0 3 89 87 90
		f 3 -192 193 194
		mu 0 3 90 87 81
		f 3 195 -193 196
		mu 0 3 91 89 90
		f 3 197 198 -197
		mu 0 3 90 92 91
		f 3 -198 199 200
		mu 0 3 92 90 80
		f 3 201 202 -201
		mu 0 3 80 93 92
		f 3 -202 203 204
		mu 0 3 93 80 94
		f 3 205 206 -205
		mu 0 3 94 95 93
		f 3 -206 207 208
		mu 0 3 95 94 96
		f 3 209 210 -208
		mu 0 3 94 97 96
		f 3 -211 211 212
		mu 0 3 96 97 98
		f 3 213 214 -212
		mu 0 3 97 99 98
		f 3 215 -214 216
		mu 0 3 76 99 97
		f 3 -216 217 218
		mu 0 3 99 76 100
		f 3 219 -213 220
		mu 0 3 101 96 98
		f 3 -210 221 222
		mu 0 3 97 94 78
		f 3 -220 223 -209
		mu 0 3 96 101 95
		f 3 -196 224 225
		mu 0 3 89 91 102
		f 3 226 227 -226
		mu 0 3 102 103 89
		f 3 -227 228 229
		mu 0 3 103 102 104
		f 3 230 231 -230
		mu 0 3 104 105 103
		f 3 232 233 -232
		mu 0 3 105 106 103
		f 3 234 235 -234
		mu 0 3 106 88 103
		f 3 236 -235 237
		mu 0 3 107 88 106
		f 3 238 239 -238
		mu 0 3 106 108 107
		f 3 240 -240 241
		mu 0 3 109 107 108
		f 3 242 243 -242
		mu 0 3 108 110 109
		f 3 244 -244 245
		mu 0 3 111 109 110
		f 3 246 -246 247
		mu 0 3 112 111 110
		f 3 248 -248 249
		mu 0 3 113 112 110
		f 3 250 251 -249
		mu 0 3 113 114 112
		f 3 252 -251 253
		mu 0 3 115 114 113
		f 3 254 -254 255
		mu 0 3 116 115 113
		f 3 -256 256 257
		mu 0 3 116 113 108
		f 3 258 -255 259
		mu 0 3 117 115 116
		f 3 260 261 -260
		mu 0 3 116 105 117
		f 3 262 -262 263
		mu 0 3 118 117 105
		f 3 -263 264 265
		mu 0 3 117 118 119
		f 3 266 -266 267
		mu 0 3 120 117 119
		f 3 268 -268 269
		mu 0 3 121 120 119
		f 3 270 -269 271
		mu 0 3 122 120 121
		f 3 272 273 -271
		mu 0 3 122 115 120
		f 3 -259 -267 -274
		mu 0 3 115 117 120
		f 3 -273 274 -253
		mu 0 3 115 122 114
		f 3 -247 275 276
		mu 0 3 111 112 123
		f 3 277 278 -277
		mu 0 3 123 124 111
		f 3 279 -279 280
		mu 0 3 125 111 124
		f 3 281 -281 282
		mu 0 3 126 125 124
		f 3 283 -283 284
		mu 0 3 127 126 124
		f 3 -284 285 286
		mu 0 3 126 127 128
		f 3 287 288 -287
		mu 0 3 128 129 126
		f 3 289 290 -289
		mu 0 3 129 130 126
		f 3 291 292 -291
		mu 0 3 130 131 126
		f 3 -292 293 294
		mu 0 3 131 130 132
		f 3 -295 295 296
		mu 0 3 131 132 133
		f 3 -297 297 298
		mu 0 3 131 133 134
		f 3 -298 299 300
		mu 0 3 134 133 135
		f 3 -301 301 302
		mu 0 3 134 135 136
		f 3 -302 303 304
		mu 0 3 136 135 137
		f 3 305 -305 306
		mu 0 3 138 136 137
		f 3 -307 307 308
		mu 0 3 138 137 139
		f 3 309 -309 310
		mu 0 3 140 138 139
		f 3 311 -311 312
		mu 0 3 141 140 139
		f 3 -313 313 314
		mu 0 3 141 139 142
		f 3 315 316 -315
		mu 0 3 142 143 141
		f 3 317 318 -317
		mu 0 3 143 144 141
		f 3 -318 319 320
		mu 0 3 144 143 77
		f 3 -316 321 322
		mu 0 3 143 142 70
		f 3 323 -314 324
		mu 0 3 145 142 139
		f 3 -324 325 326
		mu 0 3 142 145 69
		f 3 327 -326 328
		mu 0 3 146 69 145
		f 3 329 330 -329
		mu 0 3 145 147 146
		f 3 331 -331 332
		mu 0 3 148 146 147
		f 3 333 -333 334
		mu 0 3 149 148 147
		f 3 335 -335 336
		mu 0 3 135 149 147
		f 3 337 338 -334
		mu 0 3 149 150 148
		f 3 339 340 -339
		mu 0 3 150 151 148
		f 3 -340 341 342
		mu 0 3 151 150 152
		f 3 343 344 -343
		mu 0 3 152 66 151
		f 3 -344 345 346
		mu 0 3 66 152 51
		f 3 347 -342 348
		mu 0 3 27 152 150
		f 3 -348 349 350
		mu 0 3 152 27 153
		f 3 351 -350 352
		mu 0 3 154 153 27
		f 3 -352 353 354
		mu 0 3 153 154 34
		f 3 355 -355 356
		mu 0 3 155 153 34
		f 3 -356 357 358
		mu 0 3 153 155 50
		f 3 -351 -359 359
		mu 0 3 152 153 50
		f 3 -338 360 361
		mu 0 3 150 149 25
		f 3 -332 -341 362
		mu 0 3 146 148 151
		f 3 363 364 -363
		mu 0 3 151 67 146
		f 3 -330 365 366
		mu 0 3 147 145 137
		f 3 367 -312 -319
		mu 0 3 144 140 141
		f 3 -368 368 369
		mu 0 3 140 144 82
		f 3 -310 370 371
		mu 0 3 138 140 84
		f 3 372 373 -372
		mu 0 3 84 156 138
		f 3 -366 -325 -308
		mu 0 3 137 145 139
		f 3 -306 -374 374
		mu 0 3 136 138 156
		f 3 -337 -367 -304
		mu 0 3 135 147 137
		f 3 375 -303 -375
		mu 0 3 156 134 136
		f 3 -376 376 377
		mu 0 3 134 156 157
		f 3 -377 378 379
		mu 0 3 157 156 85
		f 3 380 -380 381
		mu 0 3 158 157 85
		f 3 382 383 -381
		mu 0 3 158 159 157
		f 3 384 385 -384
		mu 0 3 159 125 157
		f 3 386 387 -383
		mu 0 3 158 109 159
		f 3 388 -378 -386
		mu 0 3 125 134 157
		f 3 389 -336 -300
		mu 0 3 133 149 135
		f 3 390 391 -390
		mu 0 3 133 24 149
		f 3 392 -299 -389
		mu 0 3 125 131 134
		f 3 393 -391 -296
		mu 0 3 132 24 133
		f 3 394 -294 395
		mu 0 3 160 132 130
		f 3 396 -396 397
		mu 0 3 161 160 130
		f 3 -397 398 399
		mu 0 3 160 161 162
		f 3 -400 400 401
		mu 0 3 160 162 21
		f 3 -401 402 403
		mu 0 3 21 162 163
		f 3 -395 404 405
		mu 0 3 132 160 22
		f 3 -290 406 -398
		mu 0 3 130 129 161
		f 3 -282 -293 -393
		mu 0 3 125 126 131
		f 3 -280 -385 407
		mu 0 3 111 125 159
		f 3 -278 408 -285
		mu 0 3 124 123 127
		f 3 -245 -408 -388
		mu 0 3 109 111 159
		f 3 -243 -257 -250
		mu 0 3 110 108 113
		f 3 -241 -387 409
		mu 0 3 107 109 158
		f 3 410 411 -410
		mu 0 3 158 86 107
		f 3 412 -258 -239
		mu 0 3 106 116 108
		f 3 -261 -413 -233
		mu 0 3 105 116 106
		f 3 -264 -231 413
		mu 0 3 118 105 104
		f 3 -190 -228 -236
		mu 0 3 88 89 103
		f 3 -237 -412 -189
		mu 0 3 88 107 86
		f 3 -411 -382 -184
		mu 0 3 86 158 85
		f 3 -373 -182 -379
		mu 0 3 156 84 85
		f 3 -180 -371 -370
		mu 0 3 82 84 140
		f 3 -187 -178 -194
		mu 0 3 87 83 81
		f 3 -176 -369 414
		mu 0 3 79 82 144
		f 3 -195 -174 -200
		mu 0 3 90 81 80
		f 3 -172 -222 -204
		mu 0 3 80 78 94
		f 3 -170 -415 -321
		mu 0 3 77 79 144
		f 3 -168 -217 -223
		mu 0 3 78 76 97
		f 3 -166 -320 415
		mu 0 3 74 77 143
		f 3 -164 416 -218
		mu 0 3 76 75 100
		f 3 417 -161 -416
		mu 0 3 143 71 74
		f 3 -323 -153 -418
		mu 0 3 143 70 71
		f 3 -150 -322 -327
		mu 0 3 69 70 142
		f 3 -328 -365 -148
		mu 0 3 69 146 67
		f 3 -364 -345 -145
		mu 0 3 67 151 66
		f 3 -138 -154 -146
		mu 0 3 65 64 68
		f 3 -136 418 -157
		mu 0 3 64 63 72
		f 3 -140 419 -132
		mu 0 3 62 53 60
		f 3 -114 -129 -420
		mu 0 3 53 54 60
		f 3 -112 -143 -347
		mu 0 3 51 53 66
		f 3 -110 420 -116
		mu 0 3 52 49 55
		f 3 -108 -346 -360
		mu 0 3 50 51 152
		f 3 -106 -358 421
		mu 0 3 47 50 155
		f 3 -104 -122 -421
		mu 0 3 49 48 55
		f 3 -102 422 -124
		mu 0 3 48 45 58
		f 3 423 -100 -422
		mu 0 3 155 46 47
		f 3 424 425 -424
		mu 0 3 155 35 46
		f 3 -98 426 427
		mu 0 3 43 46 37
		f 3 -96 428 -423
		mu 0 3 45 44 58
		f 3 429 -88 430
		mu 0 3 164 41 40
		f 3 431 -431 432
		mu 0 3 165 164 40
		f 3 433 -433 434
		mu 0 3 166 165 40
		f 3 435 -434 436
		mu 0 3 167 165 166
		f 3 437 -437 438
		mu 0 3 168 167 166
		f 3 439 440 -439
		mu 0 3 166 169 168
		f 3 441 442 -441
		mu 0 3 169 170 168
		f 3 443 -443 444
		mu 0 3 171 168 170
		f 3 -445 445 446
		mu 0 3 171 170 172
		f 3 447 -446 448
		mu 0 3 173 172 170
		f 3 449 -449 450
		mu 0 3 174 173 170
		f 3 -450 451 452
		mu 0 3 173 174 175
		f 3 453 454 -453
		mu 0 3 175 10 173
		f 3 455 -455 456
		mu 0 3 176 173 10
		f 3 -454 457 458
		mu 0 3 10 175 177
		f 3 459 460 -458
		mu 0 3 175 178 177
		f 3 461 -461 462
		mu 0 3 13 177 178
		f 3 463 464 -463
		mu 0 3 178 17 13
		f 3 -464 465 466
		mu 0 3 17 178 30
		f 3 -460 467 468
		mu 0 3 178 175 32
		f 3 -468 -452 469
		mu 0 3 32 175 174
		f 3 470 -470 471
		mu 0 3 179 32 174
		f 3 472 -472 473
		mu 0 3 169 179 174
		f 3 -473 474 475
		mu 0 3 179 169 36
		f 3 -456 476 -448
		mu 0 3 173 176 172
		f 3 -444 477 478
		mu 0 3 168 171 180
		f 3 -442 -474 -451
		mu 0 3 170 169 174
		f 3 -440 479 480
		mu 0 3 169 166 38
		f 3 -479 481 -438
		mu 0 3 168 180 167
		f 3 482 483 -482
		mu 0 3 180 181 167
		f 3 484 485 -484
		mu 0 3 181 182 167
		f 3 486 487 -485
		mu 0 3 181 183 182
		f 3 488 -488 489
		mu 0 3 184 182 183
		f 3 490 491 -490
		mu 0 3 183 185 184
		f 3 492 493 -492
		mu 0 3 185 186 184
		f 3 -494 494 495
		mu 0 3 184 186 187
		f 3 -496 496 497
		mu 0 3 184 187 188
		f 3 -497 498 499
		mu 0 3 188 187 189
		f 3 500 -500 501
		mu 0 3 164 188 189
		f 3 502 503 -502
		mu 0 3 189 190 164
		f 3 504 -493 505
		mu 0 3 191 186 185
		f 3 506 507 -506
		mu 0 3 185 192 191
		f 3 508 -508 509
		mu 0 3 193 191 192
		f 3 510 -510 511
		mu 0 3 194 193 192
		f 3 512 -512 513
		mu 0 3 195 194 192
		f 3 514 515 -514
		mu 0 3 192 196 195
		f 3 -516 516 517
		mu 0 3 195 196 197
		f 3 518 519 -517
		mu 0 3 196 198 197
		f 3 -519 520 521
		mu 0 3 198 196 183
		f 3 -513 522 523
		mu 0 3 194 195 199
		f 3 524 -524 525
		mu 0 3 200 194 199
		f 3 526 -525 527
		mu 0 3 201 194 200
		f 3 528 529 -528
		mu 0 3 200 202 201
		f 3 530 -530 531
		mu 0 3 203 201 202
		f 3 532 533 -532
		mu 0 3 202 204 203
		f 3 534 -534 535
		mu 0 3 205 203 204
		f 3 536 -536 537
		mu 0 3 206 205 204
		f 3 -533 538 539
		mu 0 3 204 202 207
		f 3 -531 540 541
		mu 0 3 201 203 208
		f 3 542 -542 543
		mu 0 3 209 201 208
		f 3 -543 544 545
		mu 0 3 201 209 193
		f 3 -529 546 -539
		mu 0 3 202 200 207
		f 3 -527 -546 -511
		mu 0 3 194 201 193
		f 3 547 -509 -545
		mu 0 3 209 191 193
		f 3 -515 -507 548
		mu 0 3 196 192 185
		f 3 -549 -491 -521
		mu 0 3 196 185 183
		f 3 -489 -498 549
		mu 0 3 182 184 188
		f 3 -550 550 551
		mu 0 3 182 188 165
		f 3 -487 552 -522
		mu 0 3 183 181 198
		f 3 -553 553 554
		mu 0 3 198 181 210
		f 3 -483 555 -554
		mu 0 3 181 180 210
		f 3 -486 -552 -436
		mu 0 3 167 182 165
		f 3 -501 -432 -551
		mu 0 3 188 164 165
		f 3 556 -430 -504
		mu 0 3 190 41 164
		f 3 -86 -480 -435
		mu 0 3 40 38 166
		f 3 -93 -428 -85
		mu 0 3 39 43 37
		f 3 -82 -475 -481
		mu 0 3 38 36 169
		f 3 -80 -427 -426
		mu 0 3 35 37 46
		f 3 -78 557 -476
		mu 0 3 36 33 179
		f 3 -425 -357 -77
		mu 0 3 35 155 34
		f 3 -74 -354 558
		mu 0 3 31 34 154
		f 3 -72 -471 -558
		mu 0 3 33 32 179
		f 3 -70 -466 -469
		mu 0 3 32 30 178
		f 3 -68 -559 559
		mu 0 3 28 31 154
		f 3 -60 -560 -353
		mu 0 3 27 28 154
		f 3 -59 -349 -362
		mu 0 3 25 27 150
		f 3 -56 560 -63
		mu 0 3 26 23 29
		f 3 -361 -392 -55
		mu 0 3 25 149 24
		f 3 -406 -53 -394
		mu 0 3 132 22 24
		f 3 561 -561 -50
		mu 0 3 19 29 23
		f 3 -48 -405 -402
		mu 0 3 21 22 160
		f 3 -404 562 -47
		mu 0 3 21 163 20
		f 3 -563 563 564
		mu 0 3 20 163 211
		f 3 -565 565 566
		mu 0 3 20 211 15
		f 3 567 -566 568
		mu 0 3 212 15 211
		f 3 -42 -64 -562
		mu 0 3 19 18 29
		f 3 -66 -40 -467
		mu 0 3 30 18 17
		f 3 -567 -36 -45
		mu 0 3 20 15 16
		f 3 -568 569 -35
		mu 0 3 15 212 3
		f 3 -30 -465 -39
		mu 0 3 14 13 17
		f 3 -462 -28 570
		mu 0 3 177 13 11
		f 3 -22 -459 -571
		mu 0 3 11 10 177
		f 3 -20 571 -457
		mu 0 3 10 8 176
		f 3 -6 -570 572
		mu 0 3 4 3 212
		f 3 -4 -27 -33
		mu 0 3 3 2 12
		f 3 -2 -19 -24
		mu 0 3 2 1 9
		f 3 -1 -9 -14
		mu 0 3 1 0 5
		f 3 573 574 575
		mu 0 3 213 214 215
		f 3 576 -576 577
		mu 0 3 216 213 215
		f 3 578 579 -578
		mu 0 3 215 217 216
		f 3 580 581 -580
		mu 0 3 217 218 216
		f 3 -581 582 583
		mu 0 3 218 217 219
		f 3 -584 584 585
		mu 0 3 218 219 220
		f 3 586 587 -585
		mu 0 3 219 221 220
		f 3 588 589 -588
		mu 0 3 221 222 220
		f 3 -589 590 591
		mu 0 3 222 221 223
		f 3 592 -591 593
		mu 0 3 224 223 221
		f 3 594 -594 595
		mu 0 3 225 224 221
		f 3 596 -595 597
		mu 0 3 226 224 225
		f 3 598 599 -598
		mu 0 3 225 227 226
		f 3 -600 600 601
		mu 0 3 226 227 228
		f 3 602 603 -602
		mu 0 3 228 229 226
		f 3 604 605 -604
		mu 0 3 229 230 226
		f 3 -605 606 607
		mu 0 3 230 229 231
		f 3 608 609 -608
		mu 0 3 231 232 230
		f 3 -610 610 611
		mu 0 3 230 232 233
		f 3 612 613 -611
		mu 0 3 232 234 233
		f 3 614 -614 615
		mu 0 3 235 233 234
		f 3 -616 616 617
		mu 0 3 235 234 236
		f 3 618 619 -617
		mu 0 3 234 237 236
		f 3 -620 620 621
		mu 0 3 236 237 238
		f 3 622 623 -621
		mu 0 3 237 239 238
		f 3 624 -624 625
		mu 0 3 240 238 239
		f 3 626 627 -626
		mu 0 3 239 241 240
		f 3 628 -628 629
		mu 0 3 242 240 241
		f 3 630 631 -630
		mu 0 3 241 243 242
		f 3 632 -632 633
		mu 0 3 244 242 243
		f 3 634 635 -634
		mu 0 3 243 245 244
		f 3 636 -636 637
		mu 0 3 246 244 245
		f 3 638 639 -638
		mu 0 3 245 247 246
		f 3 640 -640 641
		mu 0 3 248 246 247
		f 3 642 643 -642
		mu 0 3 247 249 248
		f 3 644 -644 645
		mu 0 3 250 248 249
		f 3 646 -646 647
		mu 0 3 251 250 249
		f 3 648 649 -648
		mu 0 3 249 252 251
		f 3 650 651 -650
		mu 0 3 252 253 251
		f 3 652 -652 653
		mu 0 3 254 251 253
		f 3 654 655 -654
		mu 0 3 253 255 254
		f 3 656 -656 657
		mu 0 3 256 254 255
		f 3 -658 658 659
		mu 0 3 256 255 257
		f 3 660 661 -659
		mu 0 3 255 258 257
		f 3 662 663 -662
		mu 0 3 258 259 257
		f 3 -664 664 665
		mu 0 3 257 259 260
		f 3 666 667 -666
		mu 0 3 260 261 257
		f 3 -667 668 669
		mu 0 3 261 260 262
		f 3 670 -669 671
		mu 0 3 263 262 260
		f 3 672 673 -672
		mu 0 3 260 264 263
		f 3 674 -674 675
		mu 0 3 265 263 264
		f 3 676 677 -676
		mu 0 3 264 266 265
		f 3 -678 678 679
		mu 0 3 265 266 267
		f 3 -680 680 681
		mu 0 3 265 267 268
		f 3 682 -682 683
		mu 0 3 269 265 268
		f 3 684 685 -684
		mu 0 3 268 270 269
		f 3 686 -686 687
		mu 0 3 271 269 270
		f 3 -687 688 689
		mu 0 3 269 271 272
		f 3 -689 690 691
		mu 0 3 272 271 273
		f 3 -691 692 693
		mu 0 3 273 271 274
		f 3 -694 694 695
		mu 0 3 273 274 275
		f 3 696 -696 697
		mu 0 3 276 273 275
		f 3 698 -698 699
		mu 0 3 277 276 275
		f 3 -700 700 701
		mu 0 3 277 275 278
		f 3 702 703 -701
		mu 0 3 275 279 278
		f 3 704 -704 705
		mu 0 3 280 278 279
		f 3 -705 706 707
		mu 0 3 278 280 281
		f 3 -707 708 709
		mu 0 3 281 280 282
		f 3 -703 710 711
		mu 0 3 279 275 283
		f 3 -702 -708 712
		mu 0 3 277 278 281
		f 3 713 714 -699
		mu 0 3 277 284 276
		f 3 715 716 -715
		mu 0 3 284 285 276
		f 3 717 718 -716
		mu 0 3 284 286 285
		f 3 719 -719 720
		mu 0 3 287 285 286
		f 3 721 722 -721
		mu 0 3 286 288 287
		f 3 723 -723 724
		mu 0 3 289 287 288
		f 3 725 726 -725
		mu 0 3 288 263 289
		f 3 727 728 -724
		mu 0 3 289 272 287
		f 3 -722 729 730
		mu 0 3 288 286 290
		f 3 731 -731 732
		mu 0 3 291 288 290
		f 3 733 -733 734
		mu 0 3 292 291 290
		f 3 735 736 -735
		mu 0 3 290 293 292
		f 3 -734 737 738
		mu 0 3 291 292 294
		f 3 739 -739 740
		mu 0 3 295 291 294
		f 3 -740 741 742
		mu 0 3 291 295 296
		f 3 743 -743 744
		mu 0 3 262 291 296
		f 3 745 -742 746
		mu 0 3 297 296 295
		f 3 -746 747 748
		mu 0 3 296 297 298
		f 3 749 750 -749
		mu 0 3 298 261 296
		f 3 -750 751 752
		mu 0 3 261 298 256
		f 3 753 -752 754
		mu 0 3 299 256 298
		f 3 755 756 -755
		mu 0 3 298 300 299
		f 3 757 -757 758
		mu 0 3 301 299 300
		f 3 -758 759 760
		mu 0 3 299 301 302
		f 3 761 -761 762
		mu 0 3 303 299 302
		f 3 763 -763 764
		mu 0 3 304 303 302
		f 3 765 -765 766
		mu 0 3 305 304 302
		f 3 767 768 -767
		mu 0 3 302 306 305
		f 3 769 770 -769
		mu 0 3 306 307 305
		f 3 771 -771 772
		mu 0 3 308 305 307
		f 3 773 774 -773
		mu 0 3 307 309 308
		f 3 775 -775 776
		mu 0 3 310 308 309
		f 3 777 778 -777
		mu 0 3 309 311 310
		f 3 779 -779 780
		mu 0 3 312 310 311
		f 3 781 782 -781
		mu 0 3 311 313 312
		f 3 783 -783 784
		mu 0 3 314 312 313
		f 3 785 786 -785
		mu 0 3 313 315 314
		f 3 787 -787 788
		mu 0 3 316 314 315
		f 3 -789 789 790
		mu 0 3 316 315 317
		f 3 -790 791 792
		mu 0 3 317 315 318
		f 3 793 794 -792
		mu 0 3 315 319 318
		f 3 -795 795 796
		mu 0 3 318 319 320
		f 3 797 798 -796
		mu 0 3 319 321 320
		f 3 -799 799 800
		mu 0 3 320 321 322
		f 3 801 802 -800
		mu 0 3 321 323 322
		f 3 803 -803 804
		mu 0 3 324 322 323
		f 3 805 -805 806
		mu 0 3 325 324 323
		f 3 807 808 -807
		mu 0 3 323 326 325
		f 3 -809 809 810
		mu 0 3 325 326 327
		f 3 811 812 -810
		mu 0 3 326 328 327
		f 3 -812 813 814
		mu 0 3 328 326 329
		f 3 815 816 -815
		mu 0 3 329 330 328
		f 3 -816 817 818
		mu 0 3 330 329 331
		f 3 -819 819 820
		mu 0 3 330 331 332
		f 3 821 822 -820
		mu 0 3 331 307 332
		f 3 823 824 -818
		mu 0 3 329 333 331
		f 3 825 826 -825
		mu 0 3 333 309 331
		f 3 827 828 -824
		mu 0 3 329 334 333
		f 3 829 830 -829
		mu 0 3 334 335 333
		f 3 831 832 -831
		mu 0 3 335 311 333
		f 3 833 -830 834
		mu 0 3 321 335 334
		f 3 -828 -814 835
		mu 0 3 334 329 326
		f 3 836 -811 837
		mu 0 3 336 325 327
		f 3 -808 838 -836
		mu 0 3 326 323 334
		f 3 839 -806 -837
		mu 0 3 336 324 325
		f 3 -802 -835 -839
		mu 0 3 323 321 334
		f 3 840 -834 -798
		mu 0 3 319 335 321
		f 3 -841 841 842
		mu 0 3 335 319 313
		f 3 843 -791 844
		mu 0 3 337 316 317;
	setAttr ".fc[500:999]"
		f 3 845 -844 846
		mu 0 3 338 316 337
		f 3 847 -847 848
		mu 0 3 339 338 337
		f 3 849 -848 850
		mu 0 3 240 338 339
		f 3 851 -851 852
		mu 0 3 340 240 339
		f 3 853 854 -846
		mu 0 3 338 341 316
		f 3 -854 855 856
		mu 0 3 341 338 242
		f 3 -788 -855 857
		mu 0 3 314 316 341
		f 3 858 859 -858
		mu 0 3 341 342 314
		f 3 -859 860 861
		mu 0 3 342 341 244
		f 3 -786 -842 -794
		mu 0 3 315 313 319
		f 3 -784 -860 862
		mu 0 3 312 314 342
		f 3 863 864 -863
		mu 0 3 342 343 312
		f 3 -864 865 866
		mu 0 3 343 342 246
		f 3 -782 -832 -843
		mu 0 3 313 311 335
		f 3 -780 -865 867
		mu 0 3 310 312 343
		f 3 868 869 -868
		mu 0 3 343 344 310
		f 3 -869 870 871
		mu 0 3 344 343 248
		f 3 -778 -826 -833
		mu 0 3 311 309 333
		f 3 -776 -870 872
		mu 0 3 308 310 344
		f 3 873 874 -873
		mu 0 3 344 345 308
		f 3 -874 875 876
		mu 0 3 345 344 250
		f 3 877 878 -877
		mu 0 3 250 346 345
		f 3 879 880 -879
		mu 0 3 346 304 345
		f 3 881 -880 882
		mu 0 3 254 304 346
		f 3 -774 -822 -827
		mu 0 3 309 307 331
		f 3 -772 -875 883
		mu 0 3 305 308 345
		f 3 -770 884 -823
		mu 0 3 307 306 332
		f 3 -766 -884 -881
		mu 0 3 304 305 345
		f 3 -882 885 -764
		mu 0 3 304 254 303
		f 3 -768 -760 886
		mu 0 3 306 302 301
		f 3 -754 -762 887
		mu 0 3 256 299 303
		f 3 -756 -748 888
		mu 0 3 300 298 297
		f 3 -732 -744 889
		mu 0 3 288 291 262
		f 3 -736 -730 890
		mu 0 3 293 290 286
		f 3 -720 -729 891
		mu 0 3 285 287 272
		f 3 -718 892 -891
		mu 0 3 286 284 293
		f 3 893 -697 -717
		mu 0 3 285 273 276
		f 3 -695 894 -711
		mu 0 3 275 274 283
		f 3 -692 -894 -892
		mu 0 3 272 273 285
		f 3 -728 895 -690
		mu 0 3 272 289 269
		f 3 -685 896 897
		mu 0 3 270 268 347
		f 3 898 899 -897
		mu 0 3 268 348 347
		f 3 -683 -896 900
		mu 0 3 265 269 289
		f 3 -899 -681 901
		mu 0 3 348 268 267
		f 3 902 903 -902
		mu 0 3 267 349 348
		f 3 904 -903 905
		mu 0 3 350 349 267
		f 3 906 907 -905
		mu 0 3 350 351 349
		f 3 908 909 -907
		mu 0 3 350 352 351
		f 3 910 911 -910
		mu 0 3 352 353 351
		f 3 -911 912 913
		mu 0 3 353 352 354
		f 3 914 915 -914
		mu 0 3 354 355 353
		f 3 916 -915 917
		mu 0 3 356 355 354
		f 3 918 -918 919
		mu 0 3 357 356 354
		f 3 920 -920 921
		mu 0 3 358 357 354
		f 3 922 923 -921
		mu 0 3 358 359 357
		f 3 924 -924 925
		mu 0 3 360 357 359
		f 3 926 927 -926
		mu 0 3 359 361 360
		f 3 928 -928 929
		mu 0 3 362 360 361
		f 3 930 931 -930
		mu 0 3 361 363 362
		f 3 932 -932 933
		mu 0 3 364 362 363
		f 3 934 935 -934
		mu 0 3 363 365 364
		f 3 936 -936 937
		mu 0 3 366 364 365
		f 3 938 -938 939
		mu 0 3 367 366 365
		f 3 940 941 -940
		mu 0 3 365 368 367
		f 3 942 943 -942
		mu 0 3 368 369 367
		f 3 944 945 -944
		mu 0 3 369 370 367
		f 3 946 -946 947
		mu 0 3 371 367 370
		f 3 948 -948 949
		mu 0 3 372 371 370
		f 3 950 -950 951
		mu 0 3 373 372 370
		f 3 952 -952 953
		mu 0 3 374 373 370
		f 3 954 955 -953
		mu 0 3 374 375 373
		f 3 956 -956 957
		mu 0 3 376 373 375
		f 3 958 -958 959
		mu 0 3 377 376 375
		f 3 960 961 -960
		mu 0 3 375 378 377
		f 3 -962 962 963
		mu 0 3 377 378 379
		f 3 964 965 -963
		mu 0 3 378 380 379
		f 3 966 -966 967
		mu 0 3 237 379 380
		f 3 -965 968 969
		mu 0 3 380 378 381
		f 3 970 -970 971
		mu 0 3 382 380 381
		f 3 972 973 -972
		mu 0 3 381 383 382
		f 3 974 -974 975
		mu 0 3 384 382 383
		f 3 976 977 -976
		mu 0 3 383 385 384
		f 3 978 979 -978
		mu 0 3 385 386 384
		f 3 980 981 -980
		mu 0 3 386 387 384
		f 3 -981 982 983
		mu 0 3 387 386 388
		f 3 984 -983 985
		mu 0 3 389 388 386
		f 3 -986 986 987
		mu 0 3 389 386 390
		f 3 988 989 -988
		mu 0 3 390 391 389
		f 3 990 991 -990
		mu 0 3 391 247 389
		f 3 -991 992 993
		mu 0 3 247 391 392
		f 3 -993 994 995
		mu 0 3 392 391 393
		f 3 996 997 -995
		mu 0 3 391 394 393
		f 3 998 999 -998
		mu 0 3 394 395 393
		f 3 1000 -1000 1001
		mu 0 3 396 393 395
		f 3 1002 1003 -1002
		mu 0 3 395 397 396
		f 3 1004 -1004 1005
		mu 0 3 398 396 397
		f 3 1006 1007 -1006
		mu 0 3 397 258 398
		f 3 -1007 1008 1009
		mu 0 3 258 397 399
		f 3 1010 -1009 1011
		mu 0 3 400 399 397
		f 3 -1011 1012 1013
		mu 0 3 399 400 401
		f 3 1014 -1013 1015
		mu 0 3 402 401 400
		f 3 1016 1017 -1016
		mu 0 3 400 403 402
		f 3 1018 -1018 1019
		mu 0 3 404 402 403
		f 3 1020 1021 -1020
		mu 0 3 403 405 404
		f 3 1022 -1022 1023
		mu 0 3 406 404 405
		f 3 1024 1025 -1024
		mu 0 3 405 407 406
		f 3 1026 -1026 1027
		mu 0 3 408 406 407
		f 3 1028 1029 -1028
		mu 0 3 407 409 408
		f 3 1030 -1030 1031
		mu 0 3 410 408 409
		f 3 1032 1033 -1032
		mu 0 3 409 378 410
		f 3 -1031 1034 1035
		mu 0 3 408 410 374
		f 3 1036 1037 -1036
		mu 0 3 374 411 408
		f 3 -1037 1038 1039
		mu 0 3 411 374 369
		f 3 -1029 1040 1041
		mu 0 3 409 407 383
		f 3 -1027 -1038 1042
		mu 0 3 406 408 411
		f 3 1043 1044 -1043
		mu 0 3 411 412 406
		f 3 -1044 1045 1046
		mu 0 3 412 411 368
		f 3 1047 1048 -1047
		mu 0 3 368 413 412
		f 3 1049 -1049 1050
		mu 0 3 414 412 413
		f 3 1051 1052 -1051
		mu 0 3 413 415 414
		f 3 1053 -1053 1054
		mu 0 3 416 414 415
		f 3 1055 1056 -1055
		mu 0 3 415 417 416
		f 3 1057 -1057 1058
		mu 0 3 418 416 417
		f 3 1059 1060 -1059
		mu 0 3 417 419 418
		f 3 1061 -1061 1062
		mu 0 3 420 418 419
		f 3 -1063 1063 1064
		mu 0 3 420 419 421
		f 3 -1065 1065 1066
		mu 0 3 420 421 266
		f 3 1067 -1066 1068
		mu 0 3 350 266 421
		f 3 1069 1070 -1064
		mu 0 3 419 422 421
		f 3 1071 1072 -1071
		mu 0 3 422 358 421
		f 3 1073 1074 -1073
		mu 0 3 358 352 421
		f 3 -1062 1075 1076
		mu 0 3 418 420 423
		f 3 1077 1078 -1077
		mu 0 3 423 401 418
		f 3 1079 1080 -1076
		mu 0 3 420 259 423
		f 3 1081 1082 -1081
		mu 0 3 259 399 423
		f 3 -1080 1083 1084
		mu 0 3 259 420 264
		f 3 -1060 1085 -1070
		mu 0 3 419 417 422
		f 3 1086 1087 -1086
		mu 0 3 417 424 422
		f 3 1088 1089 -1088
		mu 0 3 424 359 422
		f 3 -1058 -1079 1090
		mu 0 3 416 418 401
		f 3 -1056 1091 -1087
		mu 0 3 417 415 424
		f 3 1092 1093 -1092
		mu 0 3 415 425 424
		f 3 1094 1095 -1094
		mu 0 3 425 361 424
		f 3 -1054 1096 1097
		mu 0 3 414 416 402
		f 3 -1052 1098 -1093
		mu 0 3 415 413 425
		f 3 1099 1100 -1099
		mu 0 3 413 426 425
		f 3 1101 1102 -1101
		mu 0 3 426 363 425
		f 3 -1050 1103 1104
		mu 0 3 412 414 404
		f 3 -1048 1105 -1100
		mu 0 3 413 368 426
		f 3 -1025 1106 1107
		mu 0 3 407 405 385
		f 3 1108 -1107 1109
		mu 0 3 394 385 405
		f 3 -1109 1110 1111
		mu 0 3 385 394 390
		f 3 -1023 -1045 -1105
		mu 0 3 404 406 412
		f 3 -1021 1112 -1110
		mu 0 3 405 403 394
		f 3 -1019 -1104 -1098
		mu 0 3 402 404 414
		f 3 -1017 1113 1114
		mu 0 3 403 400 395
		f 3 -1015 -1097 -1091
		mu 0 3 401 402 416
		f 3 -1078 -1083 -1014
		mu 0 3 401 423 399
		f 3 -1005 1115 1116
		mu 0 3 396 398 253
		f 3 -1003 -1114 -1012
		mu 0 3 397 395 400
		f 3 -1001 1117 1118
		mu 0 3 393 396 252
		f 3 -999 -1113 -1115
		mu 0 3 395 394 403
		f 3 -1119 1119 -996
		mu 0 3 393 252 392
		f 3 -997 -989 -1111
		mu 0 3 394 391 390
		f 3 -985 1120 1121
		mu 0 3 388 389 245
		f 3 1122 1123 -984
		mu 0 3 388 427 387
		f 3 1124 -1124 1125
		mu 0 3 428 387 427
		f 3 -1126 1126 1127
		mu 0 3 428 427 239
		f 3 1128 -1128 1129
		mu 0 3 380 428 239
		f 3 -1125 1130 1131
		mu 0 3 387 428 382
		f 3 -1123 1132 1133
		mu 0 3 427 388 243
		f 3 -979 -1112 -987
		mu 0 3 386 385 390
		f 3 -977 -1041 -1108
		mu 0 3 385 383 407
		f 3 -975 -982 -1132
		mu 0 3 382 384 387
		f 3 -973 1134 -1042
		mu 0 3 383 381 409
		f 3 -971 -1131 -1129
		mu 0 3 380 382 428
		f 3 -1033 -1135 -969
		mu 0 3 378 409 381
		f 3 1135 1136 -964
		mu 0 3 379 232 377
		f 3 -961 1137 -1034
		mu 0 3 378 375 410
		f 3 -959 1138 1139
		mu 0 3 376 377 231
		f 3 1140 -1140 1141
		mu 0 3 429 376 231
		f 3 1142 -1141 1143
		mu 0 3 430 376 429
		f 3 1144 1145 -1144
		mu 0 3 429 431 430
		f 3 -1146 1146 1147
		mu 0 3 430 431 432
		f 3 1148 1149 -1147
		mu 0 3 431 433 432
		f 3 1150 -1150 1151
		mu 0 3 434 432 433
		f 3 1152 1153 -1152
		mu 0 3 433 435 434
		f 3 1154 1155 -1154
		mu 0 3 435 436 434
		f 3 1156 1157 -1156
		mu 0 3 436 437 434
		f 3 -1157 1158 1159
		mu 0 3 437 436 438
		f 3 1160 -1160 1161
		mu 0 3 439 437 438
		f 3 -1162 1162 1163
		mu 0 3 439 438 440
		f 3 1164 1165 -1164
		mu 0 3 440 441 439
		f 3 1166 -1166 1167
		mu 0 3 372 439 441
		f 3 1168 1169 -1167
		mu 0 3 372 442 439
		f 3 1170 -1169 1171
		mu 0 3 443 442 372
		f 3 -1171 1172 1173
		mu 0 3 442 443 430
		f 3 -1165 1174 1175
		mu 0 3 441 440 444
		f 3 1176 -1175 1177
		mu 0 3 445 444 440
		f 3 1178 1179 -1178
		mu 0 3 440 446 445
		f 3 -1180 1180 1181
		mu 0 3 445 446 447
		f 3 1182 -1181 1183
		mu 0 3 448 447 446
		f 3 1184 1185 -1184
		mu 0 3 446 436 448
		f 3 1186 -1186 1187
		mu 0 3 449 448 436
		f 3 -1187 1188 1189
		mu 0 3 448 449 450
		f 3 1190 1191 -1190
		mu 0 3 450 451 448
		f 3 -1191 1192 1193
		mu 0 3 451 450 452
		f 3 1194 1195 -1194
		mu 0 3 452 453 451
		f 3 1196 -1196 1197
		mu 0 3 454 451 453
		f 3 1198 -1198 1199
		mu 0 3 455 454 453
		f 3 1200 -1200 1201
		mu 0 3 456 455 453
		f 3 -1201 1202 1203
		mu 0 3 455 456 457
		f 3 1204 1205 -1204
		mu 0 3 457 458 455
		f 3 1206 1207 -1206
		mu 0 3 458 459 455
		f 3 -1207 1208 1209
		mu 0 3 459 458 460
		f 3 1210 -1210 1211
		mu 0 3 461 459 460
		f 3 -1212 1212 1213
		mu 0 3 461 460 462
		f 3 1214 1215 -1214
		mu 0 3 462 463 461
		f 3 1216 -1216 1217
		mu 0 3 464 461 463
		f 3 1218 -1218 1219
		mu 0 3 465 464 463
		f 3 -1220 1220 1221
		mu 0 3 465 463 466
		f 3 -1222 1222 1223
		mu 0 3 465 466 467
		f 3 1224 1225 -1224
		mu 0 3 467 468 465
		f 3 1226 1227 -1226
		mu 0 3 468 469 465
		f 3 -1227 1228 1229
		mu 0 3 469 468 470
		f 3 1230 -1229 1231
		mu 0 3 471 470 468
		f 3 -1232 1232 1233
		mu 0 3 471 468 472
		f 3 -1234 1234 1235
		mu 0 3 471 472 473
		f 3 1236 -1235 1237
		mu 0 3 474 473 472
		f 3 1238 1239 -1238
		mu 0 3 472 475 474
		f 3 1240 -1239 1241
		mu 0 3 467 475 472
		f 3 1242 1243 -1241
		mu 0 3 467 476 475
		f 3 -1237 1244 1245
		mu 0 3 473 474 477
		f 3 1246 -1246 1247
		mu 0 3 356 473 477
		f 3 1248 -1247 1249
		mu 0 3 478 473 356
		f 3 -1249 1250 -1236
		mu 0 3 473 478 471
		f 3 1251 -1251 1252
		mu 0 3 479 471 478
		f 3 1253 -1253 1254
		mu 0 3 360 479 478
		f 3 -1231 -1252 1255
		mu 0 3 470 471 479
		f 3 1256 -1256 1257
		mu 0 3 480 470 479
		f 3 1258 -1258 1259
		mu 0 3 362 480 479
		f 3 1260 -1257 1261
		mu 0 3 481 470 480
		f 3 1262 -1262 1263
		mu 0 3 482 481 480
		f 3 1264 -1264 1265
		mu 0 3 364 482 480
		f 3 1266 -1263 1267
		mu 0 3 483 481 482
		f 3 1268 -1268 1269
		mu 0 3 444 483 482
		f 3 1270 -1270 1271
		mu 0 3 366 444 482
		f 3 1272 -1271 1273
		mu 0 3 371 444 366
		f 3 -1267 1274 1275
		mu 0 3 481 483 484
		f 3 1276 1277 -1275
		mu 0 3 483 485 484
		f 3 1278 -1278 1279
		mu 0 3 486 484 485
		f 3 1280 1281 -1280
		mu 0 3 485 454 486
		f 3 -1282 1282 1283
		mu 0 3 486 454 459
		f 3 1284 1285 -1281
		mu 0 3 485 447 454
		f 3 -1279 1286 1287
		mu 0 3 484 486 464
		f 3 1288 -1288 1289
		mu 0 3 469 484 464
		f 3 -1277 1290 1291
		mu 0 3 485 483 445
		f 3 -1289 1292 -1276
		mu 0 3 484 469 481
		f 3 -1261 -1293 -1230
		mu 0 3 470 481 469
		f 3 -1225 -1242 -1233
		mu 0 3 468 467 472
		f 3 -1223 1293 -1243
		mu 0 3 467 466 476
		f 3 1294 1295 -1294
		mu 0 3 466 487 476
		f 3 -1295 1296 1297
		mu 0 3 487 466 462
		f 3 1298 1299 -1298
		mu 0 3 462 488 487
		f 3 -1219 -1228 -1290
		mu 0 3 464 465 469
		f 3 -1217 -1287 1300
		mu 0 3 461 464 486
		f 3 -1215 -1297 -1221
		mu 0 3 463 462 466
		f 3 -1213 1301 -1299
		mu 0 3 462 460 488
		f 3 1302 1303 -1302
		mu 0 3 460 489 488
		f 3 -1284 -1211 -1301
		mu 0 3 486 459 461
		f 3 -1303 -1209 1304
		mu 0 3 489 460 458
		f 3 1305 1306 -1305
		mu 0 3 458 490 489
		f 3 1307 1308 -1306
		mu 0 3 458 491 490
		f 3 -1205 1309 -1308
		mu 0 3 458 457 491
		f 3 -1199 -1208 -1283
		mu 0 3 454 455 459
		f 3 -1197 -1286 1310
		mu 0 3 451 454 447
		f 3 -1195 1311 -1202
		mu 0 3 453 452 456
		f 3 -1183 -1192 -1311
		mu 0 3 447 448 451
		f 3 -1182 -1285 -1292
		mu 0 3 445 447 485
		f 3 -1177 -1291 -1269
		mu 0 3 444 445 483
		f 3 1312 -1176 -1273
		mu 0 3 371 441 444
		f 3 -1163 1313 -1179
		mu 0 3 440 438 446
		f 3 1314 -1161 -1170
		mu 0 3 442 437 439
		f 3 1315 1316 -1315
		mu 0 3 442 432 437
		f 3 -1185 -1314 -1159
		mu 0 3 436 446 438
		f 3 -1155 1317 -1188
		mu 0 3 436 435 449
		f 3 1318 1319 -1153
		mu 0 3 433 492 435
		f 3 -1319 1320 1321
		mu 0 3 492 433 493
		f 3 1322 1323 -1322
		mu 0 3 493 494 492
		f 3 -1323 1324 1325
		mu 0 3 494 493 495
		f 3 1326 1327 -1325
		mu 0 3 493 496 495
		f 3 1328 -1328 1329
		mu 0 3 228 495 496
		f 3 -1329 1330 1331
		mu 0 3 495 228 497
		f 3 1332 -1332 1333
		mu 0 3 498 495 497
		f 3 1334 1335 -1334
		mu 0 3 497 499 498
		f 3 -1335 1336 1337
		mu 0 3 499 497 500
		f 3 1338 1339 -1337
		mu 0 3 497 227 500
		f 3 -1340 1340 1341
		mu 0 3 500 227 501
		f 3 1342 1343 -1342
		mu 0 3 501 502 500
		f 3 1344 -1344 1345
		mu 0 3 503 500 502
		f 3 1346 1347 -1346
		mu 0 3 502 214 503
		f 3 1348 -1343 1349
		mu 0 3 217 502 501
		f 3 -1345 1350 -1338
		mu 0 3 500 503 499
		f 3 -1327 1351 1352
		mu 0 3 496 493 431
		f 3 1353 -1326 -1333
		mu 0 3 498 494 495
		f 3 -1151 -1158 -1317
		mu 0 3 432 434 437
		f 3 -1149 -1352 -1321
		mu 0 3 433 431 493
		f 3 -1316 -1174 -1148
		mu 0 3 432 442 430
		f 3 -1145 1354 -1353
		mu 0 3 431 429 496
		f 3 1355 -1355 1356
		mu 0 3 229 496 429
		f 3 -1143 -1173 1357
		mu 0 3 376 430 443
		f 3 -957 -1358 1358
		mu 0 3 373 376 443
		f 3 -955 -1035 -1138
		mu 0 3 375 374 410
		f 3 -951 -1359 -1172
		mu 0 3 372 373 443
		f 3 -949 -1168 -1313
		mu 0 3 371 372 441
		f 3 -945 -1039 -954
		mu 0 3 370 369 374
		f 3 -943 -1046 -1040
		mu 0 3 369 368 411
		f 3 -941 1359 -1106
		mu 0 3 368 365 426
		f 3 -939 -947 -1274
		mu 0 3 366 367 371
		f 3 -937 -1272 -1265
		mu 0 3 364 366 482
		f 3 -935 -1102 -1360
		mu 0 3 365 363 426
		f 3 -933 -1266 -1259
		mu 0 3 362 364 480
		f 3 -931 -1095 -1103
		mu 0 3 363 361 425
		f 3 -929 -1260 -1254
		mu 0 3 360 362 479
		f 3 -927 -1089 -1096
		mu 0 3 361 359 424
		f 3 -925 -1255 1360
		mu 0 3 357 360 478
		f 3 -923 -1072 -1090
		mu 0 3 359 358 422
		f 3 -919 -1361 -1250
		mu 0 3 356 357 478
		f 3 -1248 1361 -917
		mu 0 3 356 477 355
		f 3 -922 -913 -1074
		mu 0 3 358 354 352
		f 3 -1075 -909 -1069
		mu 0 3 421 352 350
		f 3 -1068 -906 -679
		mu 0 3 266 350 267
		f 3 -677 -1084 -1067
		mu 0 3 266 264 420
		f 3 -675 -901 -727
		mu 0 3 263 265 289
		f 3 -671 -726 -890
		mu 0 3 262 263 288
		f 3 -751 -670 -745
		mu 0 3 296 261 262
		f 3 -665 -1085 -673
		mu 0 3 260 259 264
		f 3 -1082 -663 -1010
		mu 0 3 399 259 258
		f 3 -661 1362 -1008
		mu 0 3 258 255 398
		f 3 -668 -753 -660
		mu 0 3 257 261 256
		f 3 -657 -888 -886
		mu 0 3 254 256 303
		f 3 -655 -1116 -1363
		mu 0 3 255 253 398
		f 3 -653 -883 1363
		mu 0 3 251 254 346
		f 3 -651 -1118 -1117
		mu 0 3 253 252 396
		f 3 -649 1364 -1120
		mu 0 3 252 249 392
		f 3 -647 -1364 -878
		mu 0 3 250 251 346
		f 3 -645 -876 -872
		mu 0 3 248 250 344
		f 3 -1365 -643 -994
		mu 0 3 392 249 247
		f 3 -641 -871 -867
		mu 0 3 246 248 343
		f 3 -992 -639 -1121
		mu 0 3 389 247 245
		f 3 -637 -866 -862
		mu 0 3 244 246 342
		f 3 -1122 -635 -1133
		mu 0 3 388 245 243
		f 3 -633 -861 -857
		mu 0 3 242 244 341
		f 3 -1134 -631 1365
		mu 0 3 427 243 241
		f 3 -629 -856 -850
		mu 0 3 240 242 338
		f 3 -1127 -1366 -627
		mu 0 3 239 427 241
		f 3 -625 -852 1366
		mu 0 3 238 240 340
		f 3 -623 -968 -1130
		mu 0 3 239 237 380
		f 3 1367 -622 -1367
		mu 0 3 340 236 238
		f 3 -1368 1368 1369
		mu 0 3 236 340 504
		f 3 -967 -619 1370
		mu 0 3 379 237 234
		f 3 1371 -618 -1370
		mu 0 3 504 235 236
		f 3 -1372 1372 1373
		mu 0 3 235 504 505
		f 3 1374 1375 -1374
		mu 0 3 505 223 235
		f 3 -615 -1376 1376
		mu 0 3 233 235 223
		f 3 -613 -1136 -1371
		mu 0 3 234 232 379
		f 3 1377 -612 1378
		mu 0 3 224 230 233
		f 3 -609 -1139 -1137
		mu 0 3 232 231 377
		f 3 -607 -1357 -1142
		mu 0 3 231 229 429
		f 3 -1356 -603 -1330
		mu 0 3 496 229 228
		f 3 -1339 -1331 -601
		mu 0 3 227 497 228
		f 3 -599 1379 -1341
		mu 0 3 227 225 501
		f 3 1380 -1380 1381
		mu 0 3 219 501 225
		f 3 -597 -606 -1378
		mu 0 3 224 226 230
		f 3 -593 -1379 -1377
		mu 0 3 223 224 233
		f 3 -1375 1382 -592
		mu 0 3 223 505 222
		f 3 -1382 -596 -587
		mu 0 3 219 225 221
		f 3 -1381 -583 -1350
		mu 0 3 501 219 217
		f 3 -1349 -579 1383
		mu 0 3 502 217 215
		f 3 -575 -1347 -1384
		mu 0 3 215 214 502
		f 3 1384 1385 1386
		mu 0 3 506 507 508
		f 3 1387 1388 -1387
		mu 0 3 508 509 506
		f 3 1389 1390 -1389
		mu 0 3 509 510 506
		f 3 1391 1392 -1391
		mu 0 3 510 511 506
		f 3 1393 -1393 1394
		mu 0 3 512 506 511
		f 3 1395 1396 -1395
		mu 0 3 511 513 512
		f 3 -1397 1397 1398
		mu 0 3 512 513 514
		f 3 1399 1400 -1398
		mu 0 3 513 515 514
		f 3 1401 -1400 1402
		mu 0 3 516 515 513
		f 3 1403 1404 -1403
		mu 0 3 513 517 516
		f 3 1405 1406 -1405
		mu 0 3 517 518 516
		f 3 1407 1408 -1407
		mu 0 3 518 519 516
		f 3 -1408 1409 1410
		mu 0 3 519 518 520
		f 3 1411 1412 -1410
		mu 0 3 518 521 520
		f 3 -1412 1413 1414
		mu 0 3 521 518 522
		f 3 1415 -1415 1416
		mu 0 3 523 521 522
		f 3 -1417 1417 1418
		mu 0 3 523 522 524
		f 3 1419 1420 -1419
		mu 0 3 524 525 523
		f 3 -1420 1421 1422
		mu 0 3 525 524 526
		f 3 1423 -1422 1424
		mu 0 3 527 526 524
		f 3 1425 1426 -1425
		mu 0 3 524 528 527
		f 3 1427 -1427 1428
		mu 0 3 529 527 528
		f 3 1429 1430 -1429
		mu 0 3 528 530 529
		f 3 1431 -1431 1432
		mu 0 3 531 529 530
		f 3 -1433 1433 1434
		mu 0 3 531 530 532
		f 3 1435 -1434 1436
		mu 0 3 533 532 530
		f 3 1437 -1436 1438
		mu 0 3 517 532 533
		f 3 -1438 1439 1440
		mu 0 3 532 517 534
		f 3 1441 -1441 1442
		mu 0 3 535 532 534
		f 3 1443 -1443 1444
		mu 0 3 511 535 534
		f 3 -1435 -1442 1445
		mu 0 3 531 532 535
		f 3 1446 -1446 1447
		mu 0 3 510 531 535
		f 3 -1447 1448 1449
		mu 0 3 531 510 536
		f 3 1450 1451 -1450
		mu 0 3 536 537 531
		f 3 -1451 1452 1453
		mu 0 3 537 536 538
		f 3 1454 1455 -1454
		mu 0 3 538 539 537
		f 3 1456 -1456 1457
		mu 0 3 540 537 539
		f 3 1458 1459 -1458
		mu 0 3 539 541 540
		f 3 1460 -1460 1461
		mu 0 3 542 540 541
		f 3 1462 -1462 1463
		mu 0 3 543 542 541
		f 3 -1464 1464 1465
		mu 0 3 543 541 544
		f 3 1466 1467 -1466
		mu 0 3 544 545 543
		f 3 1468 -1468 1469
		mu 0 3 546 543 545
		f 3 1470 1471 -1470
		mu 0 3 545 547 546
		f 3 1472 -1472 1473
		mu 0 3 548 546 547
		f 3 1474 1475 -1474
		mu 0 3 547 549 548
		f 3 -1475 1476 1477
		mu 0 3 549 547 550
		f 3 1478 -1477 1479
		mu 0 3 551 550 547
		f 3 -1479 1480 1481
		mu 0 3 550 551 552
		f 3 1482 1483 -1482
		mu 0 3 552 553 550
		f 3 1484 -1484 1485
		mu 0 3 554 550 553
		f 3 1486 1487 -1486
		mu 0 3 553 555 554
		f 3 -1487 1488 1489
		mu 0 3 555 553 556
		f 3 1490 -1489 1491
		mu 0 3 557 556 553
		f 3 -1491 1492 1493
		mu 0 3 556 557 558
		f 3 1494 1495 -1494
		mu 0 3 558 559 556
		f 3 1496 -1496 1497
		mu 0 3 560 556 559
		f 3 1498 1499 -1498
		mu 0 3 559 561 560
		f 3 -1499 1500 1501
		mu 0 3 561 559 562
		f 3 1502 -1501 1503
		mu 0 3 563 562 559
		f 3 -1503 1504 1505
		mu 0 3 562 563 564
		f 3 1506 1507 -1506
		mu 0 3 564 565 562
		f 3 1508 -1508 1509
		mu 0 3 566 562 565
		f 3 1510 1511 -1510
		mu 0 3 565 567 566
		f 3 -1511 1512 1513
		mu 0 3 567 565 568
		f 3 -1513 1514 1515
		mu 0 3 568 565 569
		f 3 -1516 1516 1517
		mu 0 3 568 569 570
		f 3 1518 -1518 1519
		mu 0 3 571 568 570
		f 3 1520 1521 -1520
		mu 0 3 570 572 571
		f 3 -1522 1522 1523
		mu 0 3 571 572 573
		f 3 1524 1525 -1523
		mu 0 3 572 574 573
		f 3 1526 1527 -1526
		mu 0 3 574 575 573
		f 3 1528 -1528 1529
		mu 0 3 576 573 575
		f 3 1530 -1530 1531
		mu 0 3 577 576 575
		f 3 1532 -1532 1533
		mu 0 3 578 577 575
		f 3 -1533 1534 1535
		mu 0 3 577 578 579
		f 3 1536 1537 -1536
		mu 0 3 579 580 577
		f 3 1538 -1538 1539
		mu 0 3 581 577 580
		f 3 1540 -1540 1541
		mu 0 3 582 581 580
		f 3 -1542 1542 1543
		mu 0 3 582 580 583
		f 3 1544 1545 -1543
		mu 0 3 580 584 583
		f 3 1546 -1546 1547
		mu 0 3 585 583 584
		f 3 -1548 1548 1549
		mu 0 3 585 584 586
		f 3 -1550 1550 1551
		mu 0 3 585 586 587
		f 3 1552 1553 -1551
		mu 0 3 586 588 587
		f 3 1554 -1554 1555
		mu 0 3 589 587 588
		f 3 1556 1557 -1556
		mu 0 3 588 590 589
		f 3 -1557 1558 1559
		mu 0 3 590 588 591
		f 3 1560 1561 -1559
		mu 0 3 588 592 591
		f 3 1562 1563 -1562
		mu 0 3 592 593 591
		f 3 1564 1565 -1564
		mu 0 3 593 594 591
		f 3 -1565 1566 1567
		mu 0 3 594 593 595
		f 3 1568 1569 -1567
		mu 0 3 593 596 595
		f 3 1570 1571 -1570
		mu 0 3 596 597 595
		f 3 1572 -1572 1573
		mu 0 3 598 595 597
		f 3 1574 1575 -1574
		mu 0 3 597 599 598
		f 3 1576 -1576 1577
		mu 0 3 600 598 599
		f 3 -1578 1578 1579
		mu 0 3 600 599 601
		f 3 -1580 1580 1581
		mu 0 3 600 601 602
		f 3 1582 1583 -1581
		mu 0 3 601 603 602
		f 3 1584 -1584 1585
		mu 0 3 604 602 603
		f 3 -1586 1586 1587
		mu 0 3 604 603 605
		f 3 -1588 1588 1589
		mu 0 3 604 605 606
		f 3 1590 1591 -1589
		mu 0 3 605 607 606
		f 3 1592 1593 -1592
		mu 0 3 607 608 606
		f 3 1594 -1594 1595
		mu 0 3 609 606 608
		f 3 1596 1597 -1596
		mu 0 3 608 610 609
		f 3 1598 1599 -1598
		mu 0 3 610 611 609
		f 3 -1600 1600 1601
		mu 0 3 609 611 612
		f 3 1602 1603 -1601
		mu 0 3 611 613 612
		f 3 -1604 1604 1605
		mu 0 3 612 613 614
		f 3 1606 1607 -1605
		mu 0 3 613 615 614
		f 3 -1608 1608 1609
		mu 0 3 614 615 616
		f 3 1610 1611 -1609
		mu 0 3 615 617 616
		f 3 1612 -1612 1613
		mu 0 3 618 616 617
		f 3 1614 1615 -1614
		mu 0 3 617 619 618
		f 3 1616 -1616 1617
		mu 0 3 620 618 619
		f 3 1618 -1618 1619
		mu 0 3 621 620 619
		f 3 -1620 1620 1621
		mu 0 3 621 619 622
		f 3 1622 -1621 1623
		mu 0 3 623 622 619;
	setAttr ".fc[1000:1499]"
		f 3 -1623 1624 1625
		mu 0 3 622 623 624
		f 3 1626 -1625 1627
		mu 0 3 625 624 623
		f 3 1628 1629 -1628
		mu 0 3 623 626 625
		f 3 1630 -1630 1631
		mu 0 3 627 625 626
		f 3 1632 -1632 1633
		mu 0 3 628 627 626
		f 3 1634 -1634 1635
		mu 0 3 615 628 626
		f 3 1636 -1635 1637
		mu 0 3 629 628 615
		f 3 1638 -1637 1639
		mu 0 3 630 628 629
		f 3 1640 1641 -1640
		mu 0 3 629 631 630
		f 3 1642 1643 -1642
		mu 0 3 631 632 630
		f 3 1644 1645 -1644
		mu 0 3 632 633 630
		f 3 1646 1647 -1646
		mu 0 3 633 634 630
		f 3 -1647 1648 1649
		mu 0 3 634 633 635
		f 3 1650 -1649 1651
		mu 0 3 636 635 633
		f 3 1652 1653 -1652
		mu 0 3 633 637 636
		f 3 1654 1655 -1654
		mu 0 3 637 638 636
		f 3 1656 1657 -1656
		mu 0 3 638 639 636
		f 3 1658 1659 -1658
		mu 0 3 639 640 636
		f 3 -1659 1660 1661
		mu 0 3 640 639 641
		f 3 1662 1663 -1661
		mu 0 3 639 642 641
		f 3 1664 -1664 1665
		mu 0 3 643 641 642
		f 3 1666 1667 -1666
		mu 0 3 642 644 643
		f 3 1668 -1668 1669
		mu 0 3 645 643 644
		f 3 1670 1671 -1670
		mu 0 3 644 646 645
		f 3 1672 1673 -1672
		mu 0 3 646 647 645
		f 3 -1674 1674 1675
		mu 0 3 645 647 648
		f 3 -1676 1676 1677
		mu 0 3 645 648 649
		f 3 -1677 1678 1679
		mu 0 3 649 648 650
		f 3 1680 -1680 1681
		mu 0 3 651 649 650
		f 3 1682 -1682 1683
		mu 0 3 652 651 650
		f 3 1684 1685 -1684
		mu 0 3 650 653 652
		f 3 1686 1687 -1686
		mu 0 3 653 654 652
		f 3 -1688 1688 1689
		mu 0 3 652 654 655
		f 3 -1690 1690 1691
		mu 0 3 652 655 656
		f 3 -1691 1692 1693
		mu 0 3 656 655 657
		f 3 1694 1695 -1694
		mu 0 3 657 658 656
		f 3 1696 1697 -1696
		mu 0 3 658 651 656
		f 3 -1697 1698 1699
		mu 0 3 651 658 659
		f 3 1700 1701 -1700
		mu 0 3 659 660 651
		f 3 -1701 1702 1703
		mu 0 3 660 659 661
		f 3 1704 1705 -1704
		mu 0 3 661 662 660
		f 3 1706 -1706 1707
		mu 0 3 643 660 662
		f 3 -1707 1708 1709
		mu 0 3 660 643 649
		f 3 -1705 1710 1711
		mu 0 3 662 661 663
		f 3 1712 1713 -1712
		mu 0 3 663 641 662
		f 3 1714 -1711 1715
		mu 0 3 664 663 661
		f 3 1716 1717 -1716
		mu 0 3 661 665 664
		f 3 1718 -1718 1719
		mu 0 3 666 664 665
		f 3 1720 1721 -1720
		mu 0 3 665 667 666
		f 3 1722 -1722 1723
		mu 0 3 668 666 667
		f 3 1724 1725 -1724
		mu 0 3 667 669 668
		f 3 1726 -1726 1727
		mu 0 3 670 668 669
		f 3 1728 1729 -1728
		mu 0 3 669 671 670
		f 3 1730 -1730 1731
		mu 0 3 672 670 671
		f 3 1732 1733 -1732
		mu 0 3 671 673 672
		f 3 1734 -1734 1735
		mu 0 3 674 672 673
		f 3 1736 1737 -1736
		mu 0 3 673 675 674
		f 3 1738 1739 -1738
		mu 0 3 675 676 674
		f 3 1740 -1740 1741
		mu 0 3 677 674 676
		f 3 -1742 1742 1743
		mu 0 3 677 676 678
		f 3 -1743 1744 1745
		mu 0 3 678 676 679
		f 3 -1746 1746 1747
		mu 0 3 678 679 680
		f 3 1748 -1747 1749
		mu 0 3 681 680 679
		f 3 1750 -1750 1751
		mu 0 3 682 681 679
		f 3 1752 1753 -1752
		mu 0 3 679 683 682
		f 3 1754 1755 -1754
		mu 0 3 683 684 682
		f 3 1756 -1756 1757
		mu 0 3 685 682 684
		f 3 1758 -1758 1759
		mu 0 3 686 685 684
		f 3 1760 1761 -1760
		mu 0 3 684 687 686
		f 3 -1761 1762 1763
		mu 0 3 687 684 688
		f 3 1764 -1764 1765
		mu 0 3 689 687 688
		f 3 1766 1767 -1766
		mu 0 3 688 690 689
		f 3 1768 -1768 1769
		mu 0 3 691 689 690
		f 3 1770 1771 -1770
		mu 0 3 690 692 691
		f 3 1772 -1772 1773
		mu 0 3 693 691 692
		f 3 1774 1775 -1774
		mu 0 3 692 694 693
		f 3 1776 -1776 1777
		mu 0 3 695 693 694
		f 3 1778 1779 -1778
		mu 0 3 694 696 695
		f 3 1780 -1780 1781
		mu 0 3 697 695 696
		f 3 1782 1783 -1782
		mu 0 3 696 698 697
		f 3 1784 -1784 1785
		mu 0 3 658 697 698
		f 3 -1785 1786 1787
		mu 0 3 697 658 699
		f 3 1788 1789 -1788
		mu 0 3 699 700 697
		f 3 -1789 1790 1791
		mu 0 3 700 699 701
		f 3 1792 1793 -1791
		mu 0 3 699 702 701
		f 3 1794 1795 -1794
		mu 0 3 702 703 701
		f 3 -1796 1796 1797
		mu 0 3 701 703 704
		f 3 1798 -1798 1799
		mu 0 3 705 701 704
		f 3 1800 1801 -1800
		mu 0 3 704 706 705
		f 3 1802 1803 -1802
		mu 0 3 706 707 705
		f 3 1804 1805 -1804
		mu 0 3 707 700 705
		f 3 -1805 1806 1807
		mu 0 3 700 707 695
		f 3 -1803 1808 1809
		mu 0 3 707 706 708
		f 3 1810 1811 -1809
		mu 0 3 706 709 708
		f 3 1812 -1812 1813
		mu 0 3 710 708 709
		f 3 1814 1815 -1814
		mu 0 3 709 711 710
		f 3 1816 -1816 1817
		mu 0 3 712 710 711
		f 3 -1817 1818 1819
		mu 0 3 710 712 713
		f 3 1820 1821 -1820
		mu 0 3 713 714 710
		f 3 -1821 1822 1823
		mu 0 3 714 713 691
		f 3 1824 -1819 1825
		mu 0 3 715 713 712
		f 3 -1825 1826 1827
		mu 0 3 713 715 689
		f 3 -1815 1828 1829
		mu 0 3 711 709 716
		f 3 1830 -1829 1831
		mu 0 3 717 716 709
		f 3 -1831 1832 1833
		mu 0 3 716 717 718
		f 3 1834 -1833 1835
		mu 0 3 719 718 717
		f 3 1836 1837 -1836
		mu 0 3 717 720 719
		f 3 1838 -1838 1839
		mu 0 3 721 719 720
		f 3 1840 1841 -1840
		mu 0 3 720 703 721
		f 3 1842 1843 -1842
		mu 0 3 703 722 721
		f 3 1844 1845 -1844
		mu 0 3 722 723 721
		f 3 -1846 1846 1847
		mu 0 3 721 723 724
		f 3 1848 1849 -1847
		mu 0 3 723 725 724
		f 3 1850 -1850 1851
		mu 0 3 726 724 725
		f 3 -1851 1852 1853
		mu 0 3 724 726 719
		f 3 -1849 1854 1855
		mu 0 3 725 723 727
		f 3 1856 -1855 1857
		mu 0 3 728 727 723
		f 3 -1857 1858 1859
		mu 0 3 727 728 729
		f 3 1860 -1859 1861
		mu 0 3 730 729 728
		f 3 1862 1863 -1862
		mu 0 3 728 731 730
		f 3 1864 1865 -1864
		mu 0 3 731 732 730
		f 3 1866 -1866 1867
		mu 0 3 733 730 732
		f 3 1868 1869 -1868
		mu 0 3 732 734 733
		f 3 -1869 1870 1871
		mu 0 3 734 732 735
		f 3 1872 -1871 1873
		mu 0 3 736 735 732
		f 3 1874 -1873 1875
		mu 0 3 737 735 736
		f 3 1876 -1876 1877
		mu 0 3 738 737 736
		f 3 1878 1879 -1878
		mu 0 3 736 739 738
		f 3 1880 -1880 1881
		mu 0 3 740 738 739
		f 3 1882 -1882 1883
		mu 0 3 741 740 739
		f 3 1884 1885 -1884
		mu 0 3 739 742 741
		f 3 1886 1887 -1886
		mu 0 3 742 743 741
		f 3 1888 -1888 1889
		mu 0 3 744 741 743
		f 3 -1890 1890 1891
		mu 0 3 744 743 702
		f 3 1892 -1892 1893
		mu 0 3 657 744 702
		f 3 1894 -1889 1895
		mu 0 3 745 741 744
		f 3 1896 -1896 1897
		mu 0 3 655 745 744
		f 3 -1887 1898 1899
		mu 0 3 743 742 722
		f 3 1900 1901 -1899
		mu 0 3 742 728 722
		f 3 -1885 1902 1903
		mu 0 3 742 739 731
		f 3 -1883 -1895 1904
		mu 0 3 740 741 745
		f 3 1905 -1905 1906
		mu 0 3 654 740 745
		f 3 -1906 1907 1908
		mu 0 3 740 654 746
		f 3 1909 1910 -1909
		mu 0 3 746 747 740
		f 3 -1910 1911 1912
		mu 0 3 747 746 748
		f 3 1913 -1912 1914
		mu 0 3 749 748 746
		f 3 -1915 1915 1916
		mu 0 3 749 746 653
		f 3 1917 -1917 1918
		mu 0 3 648 749 653
		f 3 1919 -1914 1920
		mu 0 3 750 748 749
		f 3 1921 -1921 1922
		mu 0 3 647 750 749
		f 3 -1922 1923 1924
		mu 0 3 750 647 751
		f 3 1925 1926 -1925
		mu 0 3 751 752 750
		f 3 1927 1928 -1927
		mu 0 3 752 753 750
		f 3 1929 1930 -1928
		mu 0 3 752 754 753
		f 3 1931 -1931 1932
		mu 0 3 755 753 754
		f 3 1933 1934 -1933
		mu 0 3 754 756 755
		f 3 1935 1936 -1935
		mu 0 3 756 757 755
		f 3 -1937 1937 1938
		mu 0 3 755 757 758
		f 3 -1939 1939 1940
		mu 0 3 755 758 759
		f 3 -1940 1941 1942
		mu 0 3 759 758 760
		f 3 -1943 1943 1944
		mu 0 3 759 760 747
		f 3 -1944 1945 1946
		mu 0 3 747 760 738
		f 3 1947 -1942 1948
		mu 0 3 761 760 758
		f 3 1949 1950 -1949
		mu 0 3 758 762 761
		f 3 1951 1952 -1951
		mu 0 3 762 763 761
		f 3 -1953 1953 1954
		mu 0 3 761 763 764
		f 3 -1955 1955 1956
		mu 0 3 761 764 737
		f 3 1957 -1954 1958
		mu 0 3 765 764 763
		f 3 1959 1960 -1959
		mu 0 3 763 766 765
		f 3 -1960 1961 1962
		mu 0 3 766 763 767
		f 3 1963 1964 -1963
		mu 0 3 767 768 766
		f 3 -1964 1965 1966
		mu 0 3 768 767 769
		f 3 1967 -1966 1968
		mu 0 3 770 769 767
		f 3 -1969 1969 1970
		mu 0 3 770 767 762
		f 3 1971 -1971 1972
		mu 0 3 757 770 762
		f 3 -1972 1973 1974
		mu 0 3 770 757 771
		f 3 1975 1976 -1975
		mu 0 3 771 772 770
		f 3 -1976 1977 1978
		mu 0 3 772 771 773
		f 3 1979 1980 -1978
		mu 0 3 771 774 773
		f 3 1981 -1981 1982
		mu 0 3 775 773 774
		f 3 1983 -1983 1984
		mu 0 3 776 775 774
		f 3 1985 1986 -1985
		mu 0 3 774 777 776
		f 3 1987 1988 -1987
		mu 0 3 777 778 776
		f 3 1989 -1989 1990
		mu 0 3 779 776 778
		f 3 1991 -1991 1992
		mu 0 3 780 779 778
		f 3 1993 1994 -1993
		mu 0 3 778 781 780
		f 3 1995 -1995 1996
		mu 0 3 782 780 781
		f 3 -1997 1997 1998
		mu 0 3 782 781 783
		f 3 -1998 1999 2000
		mu 0 3 783 781 784
		f 3 -2001 2001 2002
		mu 0 3 783 784 785
		f 3 -2002 2003 2004
		mu 0 3 785 784 751
		f 3 -2005 2005 2006
		mu 0 3 785 751 646
		f 3 2007 -2007 2008
		mu 0 3 786 785 646
		f 3 -2008 2009 2010
		mu 0 3 785 786 787
		f 3 2011 -2010 2012
		mu 0 3 788 787 786
		f 3 -2013 2013 2014
		mu 0 3 788 786 789
		f 3 -2014 2015 2016
		mu 0 3 789 786 644
		f 3 2017 -2015 2018
		mu 0 3 790 788 789
		f 3 2019 2020 -2019
		mu 0 3 789 791 790
		f 3 2021 -2021 2022
		mu 0 3 792 790 791
		f 3 2023 -2023 2024
		mu 0 3 638 792 791
		f 3 2025 -2024 2026
		mu 0 3 793 792 638
		f 3 -2026 2027 2028
		mu 0 3 792 793 794
		f 3 2029 -2028 2030
		mu 0 3 795 794 793
		f 3 2031 -2031 2032
		mu 0 3 796 795 793
		f 3 2033 2034 -2033
		mu 0 3 793 637 796
		f 3 -2035 2035 2036
		mu 0 3 796 637 632
		f 3 2037 -2037 2038
		mu 0 3 797 796 632
		f 3 2039 2040 -2038
		mu 0 3 797 798 796
		f 3 -2040 2041 2042
		mu 0 3 798 797 799
		f 3 2043 -2042 2044
		mu 0 3 800 799 797
		f 3 -2045 2045 2046
		mu 0 3 800 797 631
		f 3 2047 -2047 2048
		mu 0 3 801 800 631
		f 3 -2048 2049 2050
		mu 0 3 800 801 802
		f 3 2051 2052 -2050
		mu 0 3 801 610 802
		f 3 2053 -2053 2054
		mu 0 3 803 802 610
		f 3 -2054 2055 2056
		mu 0 3 802 803 804
		f 3 2057 -2057 2058
		mu 0 3 805 802 804
		f 3 2059 -2059 2060
		mu 0 3 806 805 804
		f 3 2061 -2061 2062
		mu 0 3 807 806 804
		f 3 2063 2064 -2063
		mu 0 3 804 808 807
		f 3 2065 -2065 2066
		mu 0 3 809 807 808
		f 3 -2067 2067 2068
		mu 0 3 809 808 810
		f 3 -2068 2069 2070
		mu 0 3 810 808 607
		f 3 2071 2072 -2070
		mu 0 3 808 803 607
		f 3 2073 -2069 2074
		mu 0 3 811 809 810
		f 3 -2075 2075 2076
		mu 0 3 811 810 812
		f 3 -2076 2077 2078
		mu 0 3 812 810 605
		f 3 2079 -2077 2080
		mu 0 3 813 811 812
		f 3 2081 -2081 2082
		mu 0 3 814 813 812
		f 3 2083 -2083 2084
		mu 0 3 603 814 812
		f 3 2085 2086 -2082
		mu 0 3 814 815 813
		f 3 2087 -2087 2088
		mu 0 3 816 813 815
		f 3 2089 -2089 2090
		mu 0 3 817 816 815
		f 3 2091 2092 -2091
		mu 0 3 815 818 817
		f 3 2093 -2093 2094
		mu 0 3 819 817 818
		f 3 2095 2096 -2095
		mu 0 3 818 820 819
		f 3 2097 -2097 2098
		mu 0 3 821 819 820
		f 3 2099 2100 -2099
		mu 0 3 820 822 821
		f 3 2101 2102 -2101
		mu 0 3 822 823 821
		f 3 2103 -2103 2104
		mu 0 3 824 821 823
		f 3 2105 -2105 2106
		mu 0 3 825 824 823
		f 3 -2107 2107 2108
		mu 0 3 825 823 826
		f 3 2109 2110 -2109
		mu 0 3 826 584 825
		f 3 -2106 2111 2112
		mu 0 3 824 825 579
		f 3 2113 2114 -2113
		mu 0 3 579 827 824
		f 3 2115 -2115 2116
		mu 0 3 828 824 827
		f 3 2117 2118 -2117
		mu 0 3 827 829 828
		f 3 2119 -2119 2120
		mu 0 3 830 828 829
		f 3 2121 2122 -2121
		mu 0 3 829 831 830
		f 3 2123 2124 -2123
		mu 0 3 831 832 830
		f 3 2125 2126 -2125
		mu 0 3 832 833 830
		f 3 2127 2128 -2127
		mu 0 3 833 834 830
		f 3 -2128 2129 2130
		mu 0 3 834 833 817
		f 3 -2126 2131 2132
		mu 0 3 833 832 835
		f 3 -2133 2133 2134
		mu 0 3 833 835 816
		f 3 2135 2136 -2134
		mu 0 3 835 836 816
		f 3 2137 2138 -2136
		mu 0 3 835 837 836
		f 3 -2139 2139 2140
		mu 0 3 836 837 838
		f 3 -2141 2141 2142
		mu 0 3 836 838 811
		f 3 2143 2144 -2140
		mu 0 3 837 839 838
		f 3 2145 -2145 2146
		mu 0 3 840 838 839
		f 3 2147 2148 -2147
		mu 0 3 839 841 840
		f 3 2149 2150 -2149
		mu 0 3 841 842 840
		f 3 2151 2152 -2151
		mu 0 3 842 807 840
		f 3 2153 2154 -2150
		mu 0 3 841 843 842
		f 3 2155 2156 -2155
		mu 0 3 843 844 842
		f 3 2157 2158 -2157
		mu 0 3 844 806 842
		f 3 -2158 2159 2160
		mu 0 3 806 844 845
		f 3 2161 -2160 2162
		mu 0 3 846 845 844
		f 3 2163 -2163 2164
		mu 0 3 847 846 844
		f 3 2165 2166 -2164
		mu 0 3 847 848 846
		f 3 2167 2168 -2167
		mu 0 3 848 849 846
		f 3 2169 2170 -2169
		mu 0 3 849 850 846
		f 3 -2170 2171 2172
		mu 0 3 850 849 851
		f 3 -2173 2173 2174
		mu 0 3 850 851 798
		f 3 2175 2176 -2174
		mu 0 3 851 795 798
		f 3 2177 2178 -2176
		mu 0 3 851 852 795
		f 3 2179 2180 -2178
		mu 0 3 851 853 852
		f 3 2181 2182 -2181
		mu 0 3 853 854 852
		f 3 -2183 2183 2184
		mu 0 3 852 854 855
		f 3 -2185 2185 2186
		mu 0 3 852 855 794
		f 3 2187 -2186 2188
		mu 0 3 856 794 855
		f 3 2189 2190 -2189
		mu 0 3 855 857 856
		f 3 2191 -2191 2192
		mu 0 3 858 856 857
		f 3 2193 2194 -2193
		mu 0 3 857 859 858
		f 3 2195 -2195 2196
		mu 0 3 860 858 859
		f 3 2197 2198 -2197
		mu 0 3 859 861 860
		f 3 2199 -2199 2200
		mu 0 3 862 860 861
		f 3 2201 2202 -2201
		mu 0 3 861 863 862
		f 3 2203 -2203 2204
		mu 0 3 782 862 863
		f 3 2205 2206 -2205
		mu 0 3 863 864 782
		f 3 -2206 2207 2208
		mu 0 3 864 863 865
		f 3 2209 -2208 2210
		mu 0 3 866 865 863
		f 3 2211 2212 -2210
		mu 0 3 866 867 865
		f 3 2213 2214 -2213
		mu 0 3 867 868 865
		f 3 2215 -2215 2216
		mu 0 3 869 865 868
		f 3 2217 2218 -2217
		mu 0 3 868 870 869
		f 3 2219 2220 -2219
		mu 0 3 870 871 869
		f 3 -2221 2221 2222
		mu 0 3 869 871 872
		f 3 -2223 2223 2224
		mu 0 3 869 872 864
		f 3 -2224 2225 2226
		mu 0 3 864 872 780
		f 3 2227 -2222 2228
		mu 0 3 873 872 871
		f 3 2229 2230 -2229
		mu 0 3 871 874 873
		f 3 2231 2232 -2231
		mu 0 3 874 875 873
		f 3 -2233 2233 2234
		mu 0 3 873 875 876
		f 3 2235 2236 -2235
		mu 0 3 876 779 873
		f 3 2237 -2234 2238
		mu 0 3 877 876 875
		f 3 2239 2240 -2239
		mu 0 3 875 878 877
		f 3 2241 2242 -2241
		mu 0 3 878 879 877
		f 3 2243 2244 -2243
		mu 0 3 879 775 877
		f 3 -2242 2245 2246
		mu 0 3 879 878 880
		f 3 2247 -2246 2248
		mu 0 3 881 880 878
		f 3 2249 -2249 2250
		mu 0 3 882 881 878
		f 3 -2251 2251 2252
		mu 0 3 882 878 883
		f 3 2253 2254 -2253
		mu 0 3 883 884 882
		f 3 2255 -2255 2256
		mu 0 3 885 882 884
		f 3 2257 -2257 2258
		mu 0 3 886 885 884
		f 3 -2259 2259 2260
		mu 0 3 886 884 887
		f 3 2261 -2261 2262
		mu 0 3 888 886 887
		f 3 -2263 2263 2264
		mu 0 3 888 887 889
		f 3 -2264 2265 2266
		mu 0 3 889 887 890
		f 3 2267 -2267 2268
		mu 0 3 891 889 890
		f 3 -2269 2269 2270
		mu 0 3 891 890 892
		f 3 -2270 2271 2272
		mu 0 3 892 890 893
		f 3 2273 -2273 2274
		mu 0 3 894 892 893
		f 3 -2275 2275 2276
		mu 0 3 894 893 895
		f 3 2277 -2277 2278
		mu 0 3 896 894 895
		f 3 2279 -2279 2280
		mu 0 3 897 896 895
		f 3 2281 2282 -2281
		mu 0 3 895 898 897
		f 3 2283 2284 -2283
		mu 0 3 898 899 897
		f 3 2285 -2285 2286
		mu 0 3 900 897 899
		f 3 2287 -2287 2288
		mu 0 3 901 900 899
		f 3 -2289 2289 2290
		mu 0 3 901 899 902
		f 3 2291 2292 -2291
		mu 0 3 902 903 901
		f 3 2293 -2293 2294
		mu 0 3 904 901 903
		f 3 2295 2296 -2295
		mu 0 3 903 905 904
		f 3 2297 -2297 2298
		mu 0 3 906 904 905
		f 3 2299 2300 -2299
		mu 0 3 905 907 906
		f 3 2301 -2301 2302
		mu 0 3 908 906 907
		f 3 2303 2304 -2303
		mu 0 3 907 909 908
		f 3 2305 -2305 2306
		mu 0 3 910 908 909
		f 3 2307 2308 -2307
		mu 0 3 909 911 910
		f 3 2309 -2309 2310
		mu 0 3 912 910 911
		f 3 2311 2312 -2311
		mu 0 3 911 848 912
		f 3 2313 -2313 2314
		mu 0 3 913 912 848
		f 3 2315 2316 -2314
		mu 0 3 913 914 912
		f 3 2317 2318 -2317
		mu 0 3 914 915 912
		f 3 -2318 2319 2320
		mu 0 3 915 914 916
		f 3 2321 -2320 2322
		mu 0 3 917 916 914
		f 3 2323 2324 -2323
		mu 0 3 914 918 917
		f 3 2325 -2325 2326
		mu 0 3 919 917 918
		f 3 2327 -2327 2328
		mu 0 3 920 919 918
		f 3 2329 -2329 2330
		mu 0 3 913 920 918
		f 3 -2330 2331 2332
		mu 0 3 920 913 921
		f 3 2333 2334 -2332
		mu 0 3 913 847 921
		f 3 2335 -2335 2336
		mu 0 3 843 921 847
		f 3 -2336 2337 2338
		mu 0 3 921 843 922
		f 3 2339 -2339 2340
		mu 0 3 923 921 922
		f 3 2341 2342 -2341
		mu 0 3 922 924 923
		f 3 2343 -2343 2344
		mu 0 3 925 923 924
		f 3 2345 -2345 2346
		mu 0 3 926 925 924
		f 3 -2347 2347 2348
		mu 0 3 926 924 927
		f 3 2349 -2349 2350
		mu 0 3 928 926 927
		f 3 -2351 2351 2352
		mu 0 3 928 927 929
		f 3 2353 -2353 2354
		mu 0 3 832 928 929
		f 3 2355 -2352 2356
		mu 0 3 930 929 927
		f 3 2357 2358 -2357
		mu 0 3 927 931 930
		f 3 2359 2360 -2359
		mu 0 3 931 839 930
		f 3 -2356 2361 2362
		mu 0 3 929 930 837
		f 3 2363 -2350 2364
		mu 0 3 932 926 928
		f 3 2365 2366 -2365
		mu 0 3 928 831 932
		f 3 2367 -2367 2368
		mu 0 3 933 932 831
		f 3 2369 2370 -2368
		mu 0 3 933 934 932
		f 3 2371 2372 -2371
		mu 0 3 934 935 932
		f 3 2373 2374 -2372
		mu 0 3 934 936 935
		f 3 2375 2376 -2375
		mu 0 3 936 937 935
		f 3 2377 -2377 2378
		mu 0 3 925 935 937
		f 3 2379 2380 -2379
		mu 0 3 937 938 925
		f 3 -2380 2381 2382
		mu 0 3 938 937 939
		f 3 2383 -2382 2384
		mu 0 3 940 939 937
		f 3 2385 2386 -2384
		mu 0 3 940 941 939
		f 3 2387 2388 -2387
		mu 0 3 941 942 939
		f 3 2389 -2389 2390
		mu 0 3 943 939 942
		f 3 2391 2392 -2391
		mu 0 3 942 919 943
		f 3 -2392 2393 2394
		mu 0 3 919 942 944
		f 3 2395 -2394 2396
		mu 0 3 945 944 942
		f 3 2397 2398 -2396
		mu 0 3 945 946 944
		f 3 2399 2400 -2399
		mu 0 3 946 947 944
		f 3 2401 -2401 2402
		mu 0 3 948 944 947
		f 3 2403 2404 -2403
		mu 0 3 947 949 948
		f 3 -2405 2405 2406
		mu 0 3 948 949 950
		f 3 -2407 2407 2408
		mu 0 3 948 950 917
		f 3 2409 2410 -2406
		mu 0 3 949 951 950
		f 3 -2411 2411 2412
		mu 0 3 950 951 952
		f 3 -2413 2413 2414
		mu 0 3 950 952 916
		f 3 2415 -2414 2416
		mu 0 3 953 916 952
		f 3 2417 2418 -2417
		mu 0 3 952 954 953
		f 3 2419 -2419 2420
		mu 0 3 955 953 954
		f 3 2421 2422 -2421
		mu 0 3 954 956 955
		f 3 2423 -2423 2424
		mu 0 3 957 955 956
		f 3 2425 2426 -2425
		mu 0 3 956 958 957
		f 3 2427 -2427 2428
		mu 0 3 959 957 958
		f 3 2429 2430 -2429
		mu 0 3 958 960 959
		f 3 2431 -2431 2432
		mu 0 3 961 959 960
		f 3 2433 2434 -2433
		mu 0 3 960 962 961
		f 3 2435 -2435 2436
		mu 0 3 963 961 962
		f 3 2437 2438 -2437
		mu 0 3 962 964 963
		f 3 2439 -2439 2440
		mu 0 3 896 963 964
		f 3 2441 2442 -2441
		mu 0 3 964 965 896
		f 3 -2442 2443 2444
		mu 0 3 965 964 966
		f 3 -2444 2445 2446
		mu 0 3 966 964 967
		f 3 2447 -2447 2448
		mu 0 3 968 966 967
		f 3 2449 -2449 2450
		mu 0 3 969 968 967
		f 3 2451 -2451 2452
		mu 0 3 970 969 967
		f 3 -2453 2453 2454
		mu 0 3 970 967 962
		f 3 2455 -2452 2456
		mu 0 3 971 969 970
		f 3 2457 2458 -2457
		mu 0 3 970 972 971
		f 3 2459 -2459 2460
		mu 0 3 973 971 972
		f 3 2461 2462 -2461
		mu 0 3 972 974 973
		f 3 2463 -2463 2464
		mu 0 3 975 973 974
		f 3 2465 2466 -2465
		mu 0 3 974 976 975
		f 3 2467 -2467 2468
		mu 0 3 977 975 976
		f 3 2469 2470 -2469
		mu 0 3 976 978 977
		f 3 2471 -2471 2472
		mu 0 3 979 977 978
		f 3 2473 2474 -2473
		mu 0 3 978 951 979
		f 3 2475 -2475 2476
		mu 0 3 980 979 951
		f 3 -2476 2477 2478
		mu 0 3 979 980 981
		f 3 2479 -2478 2480
		mu 0 3 982 981 980
		f 3 2481 2482 -2481
		mu 0 3 980 983 982
		f 3 2483 -2483 2484
		mu 0 3 984 982 983
		f 3 2485 -2485 2486
		mu 0 3 985 984 983
		f 3 -2487 2487 2488
		mu 0 3 985 983 947
		f 3 2489 -2486 2490
		mu 0 3 552 984 985
		f 3 2491 2492 -2491
		mu 0 3 985 557 552
		f 3 -2492 2493 2494
		mu 0 3 557 985 946
		f 3 2495 2496 -2484
		mu 0 3 984 986 982
		f 3 2497 2498 -2497
		mu 0 3 986 987 982
		f 3 -2498 2499 2500
		mu 0 3 987 986 544
		f 3 2501 2502 -2501
		mu 0 3 544 988 987
		f 3 2503 -2503 2504
		mu 0 3 989 987 988
		f 3 2505 2506 -2505
		mu 0 3 988 990 989
		f 3 2507 -2507 2508
		mu 0 3 991 989 990
		f 3 2509 2510 -2509
		mu 0 3 990 992 991
		f 3 2511 -2511 2512
		mu 0 3 993 991 992
		f 3 2513 2514 -2513
		mu 0 3 992 994 993
		f 3 2515 -2515 2516
		mu 0 3 995 993 994
		f 3 2517 2518 -2517
		mu 0 3 994 996 995
		f 3 2519 -2519 2520
		mu 0 3 997 995 996
		f 3 2521 2522 -2521
		mu 0 3 996 998 997
		f 3 -2523 2523 2524
		mu 0 3 997 998 999
		f 3 -2525 2525 2526
		mu 0 3 997 999 1000
		f 3 2527 -2527 2528
		mu 0 3 1001 997 1000
		f 3 -2529 2529 2530
		mu 0 3 1001 1000 971
		f 3 2531 -2526 2532
		mu 0 3 1002 1000 999
		f 3 2533 2534 -2533
		mu 0 3 999 1003 1002
		f 3 2535 -2535 2536
		mu 0 3 1004 1002 1003
		f 3 2537 -2537 2538
		mu 0 3 1005 1004 1003
		f 3 2539 -2539 2540
		mu 0 3 1006 1005 1003
		f 3 -2540 2541 2542
		mu 0 3 1005 1006 1007
		f 3 2543 -2542 2544
		mu 0 3 1008 1007 1006
		f 3 2545 2546 -2545
		mu 0 3 1006 998 1008
		f 3 2547 -2547 2548
		mu 0 3 1009 1008 998
		f 3 -2548 2549 2550
		mu 0 3 1008 1009 1010
		f 3 2551 -2550 2552
		mu 0 3 508 1010 1009
		f 3 2553 2554 -2553
		mu 0 3 1009 1011 508
		f 3 -2554 2555 2556
		mu 0 3 1011 1009 996
		f 3 2557 2558 -2551
		mu 0 3 1010 1012 1008
		f 3 2559 2560 -2558
		mu 0 3 1010 1013 1012
		f 3 2561 2562 -2561
		mu 0 3 1013 1014 1012
		f 3 2563 2564 -2563
		mu 0 3 1014 1007 1012
		f 3 -2564 2565 2566
		mu 0 3 1007 1014 1015
		f 3 2567 -2566 2568
		mu 0 3 1016 1015 1014
		f 3 2569 2570 -2569
		mu 0 3 1014 1017 1016
		f 3 2571 2572 -2571
		mu 0 3 1017 1018 1016
		f 3 2573 -2573 2574
		mu 0 3 1019 1016 1018
		f 3 -2574 2575 2576
		mu 0 3 1016 1019 1020
		f 3 2577 2578 -2576
		mu 0 3 1019 1021 1020
		f 3 2579 -2579 2580
		mu 0 3 1022 1020 1021
		f 3 2581 2582 -2581
		mu 0 3 1021 1023 1022
		f 3 2583 -2583 2584
		mu 0 3 1024 1022 1023
		f 3 2585 2586 -2585
		mu 0 3 1023 1025 1024
		f 3 -2587 2587 2588
		mu 0 3 1024 1025 1026
		f 3 2589 2590 -2588
		mu 0 3 1025 1027 1026
		f 3 -2591 2591 2592
		mu 0 3 1026 1027 966
		f 3 2593 2594 -2590
		mu 0 3 1025 1028 1027
		f 3 2595 2596 -2595
		mu 0 3 1028 1029 1027
		f 3 2597 2598 -2597
		mu 0 3 1029 1030 1027
		f 3 2599 2600 -2599
		mu 0 3 1030 965 1027
		f 3 -2600 2601 2602
		mu 0 3 965 1030 894
		f 3 2603 -2598 2604
		mu 0 3 891 1030 1029
		f 3 2605 -2605 2606
		mu 0 3 1031 891 1029
		f 3 2607 -2607 2608
		mu 0 3 1032 1031 1029
		f 3 2609 -2608 2610
		mu 0 3 1033 1031 1032
		f 3 2611 -2611 2612
		mu 0 3 1034 1033 1032
		f 3 -2613 2613 2614
		mu 0 3 1034 1032 1035
		f 3 2615 2616 -2614
		mu 0 3 1032 1028 1035
		f 3 2617 2618 -2615
		mu 0 3 1035 1036 1034
		f 3 2619 -2619 2620
		mu 0 3 1037 1034 1036
		f 3 -2621 2621 2622
		mu 0 3 1037 1036 1038;
	setAttr ".fc[1500:1999]"
		f 3 -2622 2623 2624
		mu 0 3 1038 1036 1039
		f 3 -2624 2625 2626
		mu 0 3 1039 1036 1040
		f 3 -2627 2627 2628
		mu 0 3 1039 1040 1023
		f 3 2629 2630 -2625
		mu 0 3 1039 1041 1038
		f 3 -2630 2631 2632
		mu 0 3 1041 1039 1021
		f 3 2633 2634 -2620
		mu 0 3 1037 1042 1034
		f 3 -2618 2635 -2626
		mu 0 3 1036 1035 1040
		f 3 2636 2637 -2636
		mu 0 3 1035 1025 1040
		f 3 2638 -2612 -2635
		mu 0 3 1042 1033 1034
		f 3 -2639 2639 2640
		mu 0 3 1033 1042 1043
		f 3 2641 -2641 2642
		mu 0 3 1044 1033 1043
		f 3 -2642 2643 2644
		mu 0 3 1033 1044 1045
		f 3 2645 -2644 2646
		mu 0 3 1046 1045 1044
		f 3 -2646 2647 2648
		mu 0 3 1045 1046 1047
		f 3 2649 -2649 2650
		mu 0 3 888 1045 1047
		f 3 -2650 2651 2652
		mu 0 3 1045 888 1031
		f 3 2653 2654 -2648
		mu 0 3 1046 1048 1047
		f 3 2655 2656 -2655
		mu 0 3 1048 886 1047
		f 3 -2654 2657 2658
		mu 0 3 1048 1046 1049
		f 3 2659 2660 -2659
		mu 0 3 1049 1050 1048
		f 3 -2661 2661 2662
		mu 0 3 1048 1050 885
		f 3 2663 2664 -2662
		mu 0 3 1050 1051 885
		f 3 -2664 2665 2666
		mu 0 3 1051 1050 1052
		f 3 2667 -2666 2668
		mu 0 3 1053 1052 1050
		f 3 -2668 2669 2670
		mu 0 3 1052 1053 1054
		f 3 2671 -2671 2672
		mu 0 3 1055 1052 1054
		f 3 -2672 2673 2674
		mu 0 3 1052 1055 1056
		f 3 2675 -2674 2676
		mu 0 3 1057 1056 1055
		f 3 -2676 2677 2678
		mu 0 3 1056 1057 1058
		f 3 2679 -2679 2680
		mu 0 3 1059 1056 1058
		f 3 2681 2682 -2681
		mu 0 3 1058 1060 1059
		f 3 -2683 2683 2684
		mu 0 3 1059 1060 1061
		f 3 2685 2686 -2684
		mu 0 3 1060 1062 1061
		f 3 2687 -2687 2688
		mu 0 3 1063 1061 1062
		f 3 2689 2690 -2689
		mu 0 3 1062 1064 1063
		f 3 -2691 2691 2692
		mu 0 3 1063 1064 1065
		f 3 -2693 2693 2694
		mu 0 3 1063 1065 1066
		f 3 2695 2696 -2695
		mu 0 3 1066 1067 1063
		f 3 -2696 2697 2698
		mu 0 3 1067 1066 1068
		f 3 2699 -2699 2700
		mu 0 3 879 1067 1068
		f 3 2701 2702 -2701
		mu 0 3 1068 773 879
		f 3 2703 -2698 2704
		mu 0 3 769 1068 1066
		f 3 -2704 2705 2706
		mu 0 3 1068 769 772
		f 3 -2694 2707 2708
		mu 0 3 1066 1065 768
		f 3 2709 2710 -2690
		mu 0 3 1062 1069 1064
		f 3 2711 -2710 2712
		mu 0 3 1070 1069 1062
		f 3 2713 2714 -2712
		mu 0 3 1070 1071 1069
		f 3 2715 -2714 2716
		mu 0 3 1072 1071 1070
		f 3 2717 2718 -2717
		mu 0 3 1070 1073 1072
		f 3 2719 2720 -2719
		mu 0 3 1073 1074 1072
		f 3 2721 2722 -2721
		mu 0 3 1074 1075 1072
		f 3 2723 2724 -2722
		mu 0 3 1074 1076 1075
		f 3 -2720 2725 2726
		mu 0 3 1074 1073 1077
		f 3 2727 -2726 2728
		mu 0 3 1058 1077 1073
		f 3 -2718 2729 2730
		mu 0 3 1073 1070 1060
		f 3 -2723 2731 -2716
		mu 0 3 1072 1075 1071
		f 3 -2688 -2697 2732
		mu 0 3 1061 1063 1067
		f 3 2733 2734 -2733
		mu 0 3 1067 1078 1061
		f 3 -2734 2735 2736
		mu 0 3 1078 1067 880
		f 3 -2686 -2730 -2713
		mu 0 3 1062 1060 1070
		f 3 -2685 -2735 2737
		mu 0 3 1059 1061 1078
		f 3 2738 2739 -2738
		mu 0 3 1078 1079 1059
		f 3 -2739 2740 2741
		mu 0 3 1079 1078 881
		f 3 2742 -2742 2743
		mu 0 3 1051 1079 881
		f 3 -2729 -2731 -2682
		mu 0 3 1058 1073 1060
		f 3 -2680 -2740 2744
		mu 0 3 1056 1059 1079
		f 3 -2728 -2678 2745
		mu 0 3 1077 1058 1057
		f 3 -2675 -2745 2746
		mu 0 3 1052 1056 1079
		f 3 -2747 -2743 -2667
		mu 0 3 1052 1079 1051
		f 3 -2669 -2660 2747
		mu 0 3 1053 1050 1049
		f 3 -2645 -2653 -2610
		mu 0 3 1033 1045 1031
		f 3 2748 -2606 -2652
		mu 0 3 888 891 1031
		f 3 -2616 -2609 -2596
		mu 0 3 1028 1032 1029
		f 3 -2637 -2617 -2594
		mu 0 3 1025 1035 1028
		f 3 -2589 2749 2750
		mu 0 3 1024 1026 1004
		f 3 2751 2752 -2750
		mu 0 3 1026 968 1004
		f 3 -2586 -2628 -2638
		mu 0 3 1025 1023 1040
		f 3 -2584 2753 2754
		mu 0 3 1022 1024 1005
		f 3 2755 -2755 2756
		mu 0 3 1015 1022 1005
		f 3 -2632 -2629 -2582
		mu 0 3 1021 1039 1023
		f 3 -2580 -2756 2757
		mu 0 3 1020 1022 1015
		f 3 2758 -2633 -2578
		mu 0 3 1019 1041 1021
		f 3 -2572 2759 2760
		mu 0 3 1018 1017 1080
		f 3 2761 2762 -2760
		mu 0 3 1017 1081 1080
		f 3 -2762 2763 2764
		mu 0 3 1081 1017 1082
		f 3 -2765 2765 2766
		mu 0 3 1081 1082 1083
		f 3 2767 2768 -2766
		mu 0 3 1082 1084 1083
		f 3 -2769 2769 2770
		mu 0 3 1083 1084 1085
		f 3 2771 2772 -2770
		mu 0 3 1084 1086 1085
		f 3 2773 -2773 2774
		mu 0 3 1087 1085 1086
		f 3 2775 2776 -2775
		mu 0 3 1086 1088 1087
		f 3 -2776 2777 2778
		mu 0 3 1088 1086 1089
		f 3 -2779 2779 2780
		mu 0 3 1088 1089 514
		f 3 2781 2782 -2778
		mu 0 3 1086 507 1089
		f 3 -2782 2783 2784
		mu 0 3 507 1086 1090
		f 3 2785 -2785 2786
		mu 0 3 1013 507 1090
		f 3 2787 2788 -2787
		mu 0 3 1090 1091 1013
		f 3 2789 2790 -2788
		mu 0 3 1090 1084 1091
		f 3 -2774 2791 2792
		mu 0 3 1085 1087 1092
		f 3 -2772 -2790 -2784
		mu 0 3 1086 1084 1090
		f 3 2793 -2771 -2793
		mu 0 3 1092 1083 1085
		f 3 2794 2795 -2794
		mu 0 3 1092 1093 1083
		f 3 2796 -2796 2797
		mu 0 3 1094 1083 1093
		f 3 2798 -2798 2799
		mu 0 3 1095 1094 1093
		f 3 2800 -2791 -2768
		mu 0 3 1082 1091 1084
		f 3 2801 -2767 -2797
		mu 0 3 1094 1081 1083
		f 3 -2764 2802 -2801
		mu 0 3 1082 1017 1091
		f 3 -2570 2803 -2803
		mu 0 3 1017 1014 1091
		f 3 -2577 -2758 -2568
		mu 0 3 1016 1020 1015
		f 3 -2562 -2789 -2804
		mu 0 3 1014 1013 1091
		f 3 -2786 -2560 2804
		mu 0 3 507 1013 1010
		f 3 -2544 -2559 -2565
		mu 0 3 1007 1008 1012
		f 3 -2757 -2543 -2567
		mu 0 3 1015 1005 1007
		f 3 -2538 -2754 -2751
		mu 0 3 1004 1005 1024
		f 3 -2536 -2753 2805
		mu 0 3 1002 1004 968
		f 3 2806 -2541 -2534
		mu 0 3 999 1006 1003
		f 3 -2532 2807 2808
		mu 0 3 1000 1002 969
		f 3 -2546 -2807 -2524
		mu 0 3 998 1006 999
		f 3 -2522 -2556 -2549
		mu 0 3 998 996 1009
		f 3 -2520 -2528 2809
		mu 0 3 995 997 1001
		f 3 2810 -2810 2811
		mu 0 3 1096 995 1001
		f 3 -2812 2812 2813
		mu 0 3 1096 1001 973
		f 3 -2518 2814 -2557
		mu 0 3 996 994 1011
		f 3 2815 -2815 2816
		mu 0 3 1097 1011 994
		f 3 -2816 2817 2818
		mu 0 3 1011 1097 509
		f 3 2819 -2818 2820
		mu 0 3 536 509 1097
		f 3 -2516 -2811 2821
		mu 0 3 993 995 1096
		f 3 2822 2823 -2822
		mu 0 3 1096 1098 993
		f 3 -2823 2824 2825
		mu 0 3 1098 1096 975
		f 3 -2514 2826 -2817
		mu 0 3 994 992 1097
		f 3 2827 -2827 2828
		mu 0 3 538 1097 992
		f 3 -2512 -2824 2829
		mu 0 3 991 993 1098
		f 3 2830 2831 -2830
		mu 0 3 1098 1099 991
		f 3 -2831 2832 2833
		mu 0 3 1099 1098 977
		f 3 -2510 2834 -2829
		mu 0 3 992 990 538
		f 3 -2508 -2832 2835
		mu 0 3 989 991 1099
		f 3 2836 2837 -2836
		mu 0 3 1099 981 989
		f 3 -2506 2838 2839
		mu 0 3 990 988 539
		f 3 -2504 -2838 2840
		mu 0 3 987 989 981
		f 3 2841 -2496 2842
		mu 0 3 551 986 984
		f 3 -2842 2843 2844
		mu 0 3 986 551 545
		f 3 -2482 2845 2846
		mu 0 3 983 980 949
		f 3 -2499 -2841 -2480
		mu 0 3 982 987 981
		f 3 -2837 2847 -2479
		mu 0 3 981 1099 979
		f 3 -2472 -2848 -2834
		mu 0 3 977 979 1099
		f 3 -2470 2848 2849
		mu 0 3 978 976 954
		f 3 -2468 -2833 -2826
		mu 0 3 975 977 1098
		f 3 -2466 2850 2851
		mu 0 3 976 974 956
		f 3 -2464 -2825 -2814
		mu 0 3 973 975 1096
		f 3 -2462 2852 2853
		mu 0 3 974 972 958
		f 3 -2460 -2813 -2531
		mu 0 3 971 973 1001
		f 3 -2458 2854 2855
		mu 0 3 972 970 960
		f 3 -2456 -2530 -2809
		mu 0 3 969 971 1000
		f 3 -2450 -2808 -2806
		mu 0 3 968 969 1002
		f 3 -2752 -2593 -2448
		mu 0 3 968 1026 966
		f 3 -2601 -2445 -2592
		mu 0 3 1027 965 966
		f 3 -2438 -2454 -2446
		mu 0 3 964 962 967
		f 3 -2436 2856 2857
		mu 0 3 961 963 900
		f 3 2858 2859 -2858
		mu 0 3 900 1100 961
		f 3 -2855 -2455 -2434
		mu 0 3 960 970 962
		f 3 -2432 -2860 2860
		mu 0 3 959 961 1100
		f 3 2861 2862 -2861
		mu 0 3 1100 1101 959
		f 3 -2862 2863 2864
		mu 0 3 1101 1100 904
		f 3 -2853 -2856 -2430
		mu 0 3 958 972 960
		f 3 -2428 -2863 2865
		mu 0 3 957 959 1101
		f 3 2866 2867 -2866
		mu 0 3 1101 1102 957
		f 3 -2867 2868 2869
		mu 0 3 1102 1101 906
		f 3 -2851 -2854 -2426
		mu 0 3 956 974 958
		f 3 -2424 -2868 2870
		mu 0 3 955 957 1102
		f 3 2871 2872 -2871
		mu 0 3 1102 1103 955
		f 3 -2872 2873 2874
		mu 0 3 1103 1102 908
		f 3 -2849 -2852 -2422
		mu 0 3 954 976 956
		f 3 -2420 -2873 2875
		mu 0 3 953 955 1103
		f 3 2876 2877 -2876
		mu 0 3 1103 915 953
		f 3 -2877 2878 2879
		mu 0 3 915 1103 910
		f 3 2880 -2850 -2418
		mu 0 3 952 978 954
		f 3 -2474 -2881 -2412
		mu 0 3 951 978 952
		f 3 -2410 -2846 -2477
		mu 0 3 951 949 980
		f 3 -2404 -2488 -2847
		mu 0 3 949 947 983
		f 3 -2494 -2489 -2400
		mu 0 3 946 985 947
		f 3 2881 -2398 2882
		mu 0 3 558 946 945
		f 3 2883 2884 -2883
		mu 0 3 945 563 558
		f 3 -2884 2885 2886
		mu 0 3 563 945 941
		f 3 -2402 2887 -2395
		mu 0 3 944 948 919
		f 3 -2886 -2397 -2388
		mu 0 3 941 945 942
		f 3 2888 -2386 2889
		mu 0 3 564 941 940
		f 3 2890 2891 -2890
		mu 0 3 940 569 564
		f 3 -2891 2892 2893
		mu 0 3 569 940 936
		f 3 -2390 2894 -2383
		mu 0 3 939 943 938
		f 3 -2895 2895 2896
		mu 0 3 938 943 920
		f 3 -2897 2897 2898
		mu 0 3 938 920 923
		f 3 -2893 -2385 -2376
		mu 0 3 936 940 937
		f 3 2899 -2374 2900
		mu 0 3 570 936 934
		f 3 2901 -2370 2902
		mu 0 3 572 934 933
		f 3 -2364 -2373 2903
		mu 0 3 926 932 935
		f 3 -2358 -2348 2904
		mu 0 3 931 927 924
		f 3 -2378 -2346 -2904
		mu 0 3 935 925 926
		f 3 -2381 -2899 -2344
		mu 0 3 925 938 923
		f 3 -2342 2905 -2905
		mu 0 3 924 922 931
		f 3 2906 2907 -2906
		mu 0 3 922 841 931
		f 3 -2340 -2898 -2333
		mu 0 3 921 923 920
		f 3 -2328 -2896 -2393
		mu 0 3 919 920 943
		f 3 -2888 -2409 -2326
		mu 0 3 919 948 917
		f 3 -2322 -2408 -2415
		mu 0 3 916 917 950
		f 3 -2416 -2878 -2321
		mu 0 3 916 953 915
		f 3 -2324 -2316 -2331
		mu 0 3 918 914 913
		f 3 -2319 -2880 -2310
		mu 0 3 912 915 910
		f 3 -2308 2908 2909
		mu 0 3 911 909 853
		f 3 -2879 -2875 -2306
		mu 0 3 910 1103 908
		f 3 -2304 2910 2911
		mu 0 3 909 907 854
		f 3 2912 -2911 2913
		mu 0 3 1104 854 907
		f 3 -2874 -2870 -2302
		mu 0 3 908 1102 906
		f 3 -2300 2914 -2914
		mu 0 3 907 905 1104
		f 3 2915 -2915 2916
		mu 0 3 1105 1104 905
		f 3 -2916 2917 2918
		mu 0 3 1104 1105 857
		f 3 -2869 -2865 -2298
		mu 0 3 906 1101 904
		f 3 -2296 2919 -2917
		mu 0 3 905 903 1105
		f 3 2920 -2920 2921
		mu 0 3 1106 1105 903
		f 3 -2921 2922 2923
		mu 0 3 1105 1106 859
		f 3 -2864 2924 -2294
		mu 0 3 904 1100 901
		f 3 -2292 2925 -2922
		mu 0 3 903 902 1106
		f 3 2926 -2926 2927
		mu 0 3 866 1106 902
		f 3 -2927 2928 2929
		mu 0 3 1106 866 861
		f 3 2930 -2290 2931
		mu 0 3 867 902 899
		f 3 -2859 -2288 -2925
		mu 0 3 1100 900 901
		f 3 -2857 2932 -2286
		mu 0 3 900 963 897
		f 3 -2284 2933 -2932
		mu 0 3 899 898 867
		f 3 2934 -2282 2935
		mu 0 3 1107 898 895
		f 3 -2935 2936 2937
		mu 0 3 898 1107 868
		f 3 -2440 -2280 -2933
		mu 0 3 963 896 897
		f 3 -2278 -2443 -2603
		mu 0 3 894 896 965
		f 3 2938 -2936 -2276
		mu 0 3 893 1107 895
		f 3 2939 -2939 2940
		mu 0 3 1108 1107 893
		f 3 -2940 2941 2942
		mu 0 3 1107 1108 870
		f 3 2943 2944 -2942
		mu 0 3 1108 1109 870
		f 3 2945 2946 -2944
		mu 0 3 1108 1110 1109
		f 3 2947 -2947 2948
		mu 0 3 1111 1109 1110
		f 3 2949 -2949 2950
		mu 0 3 887 1111 1110
		f 3 -2948 2951 2952
		mu 0 3 1109 1111 874
		f 3 2953 2954 -2952
		mu 0 3 1111 883 874
		f 3 -2946 2955 2956
		mu 0 3 1110 1108 890
		f 3 -2274 -2602 2957
		mu 0 3 892 894 1030
		f 3 -2941 -2272 -2956
		mu 0 3 1108 893 890
		f 3 -2604 -2271 -2958
		mu 0 3 1030 891 892
		f 3 -2951 -2957 -2266
		mu 0 3 887 1110 890
		f 3 -2749 -2265 -2268
		mu 0 3 891 888 889
		f 3 -2657 -2262 -2651
		mu 0 3 1047 886 888
		f 3 -2950 -2260 2958
		mu 0 3 1111 887 884
		f 3 -2663 -2258 -2656
		mu 0 3 1048 885 886
		f 3 -2256 -2665 2959
		mu 0 3 882 885 1051
		f 3 -2254 -2954 -2959
		mu 0 3 884 883 1111
		f 3 -2744 -2250 -2960
		mu 0 3 1051 881 882
		f 3 -2248 -2741 -2737
		mu 0 3 880 881 1078
		f 3 -2700 -2247 -2736
		mu 0 3 1067 879 880
		f 3 -2240 2960 -2252
		mu 0 3 878 875 883
		f 3 -2238 -2245 2961
		mu 0 3 876 877 775
		f 3 -2955 -2961 -2232
		mu 0 3 874 883 875
		f 3 -2230 2962 -2953
		mu 0 3 874 871 1109
		f 3 -2228 -2237 2963
		mu 0 3 872 873 779
		f 3 -2945 -2963 -2220
		mu 0 3 870 1109 871
		f 3 -2218 -2937 -2943
		mu 0 3 870 868 1107
		f 3 -2214 -2934 -2938
		mu 0 3 868 867 898
		f 3 -2931 -2212 -2928
		mu 0 3 902 867 866
		f 3 -2216 -2225 -2209
		mu 0 3 865 869 864
		f 3 -2929 -2211 -2202
		mu 0 3 861 866 863
		f 3 -2200 2964 2965
		mu 0 3 860 862 787
		f 3 2966 -2965 2967
		mu 0 3 783 787 862
		f 3 -2923 -2930 -2198
		mu 0 3 859 1106 861
		f 3 -2196 2968 2969
		mu 0 3 858 860 788
		f 3 -2918 -2924 -2194
		mu 0 3 857 1105 859
		f 3 -2192 2970 2971
		mu 0 3 856 858 790
		f 3 2972 -2919 -2190
		mu 0 3 855 1104 857
		f 3 -2913 -2973 -2184
		mu 0 3 854 1104 855
		f 3 -2182 -2909 -2912
		mu 0 3 854 853 909
		f 3 2973 -2910 -2180
		mu 0 3 851 911 853
		f 3 -2974 -2172 2974
		mu 0 3 911 851 849
		f 3 -2312 -2975 -2168
		mu 0 3 848 911 849
		f 3 -2334 -2315 -2166
		mu 0 3 847 913 848
		f 3 -2162 -2171 2975
		mu 0 3 845 846 850
		f 3 -2976 2976 2977
		mu 0 3 845 850 799
		f 3 -2978 2978 2979
		mu 0 3 845 799 805
		f 3 -2337 -2165 -2156
		mu 0 3 843 847 844
		f 3 -2907 -2338 -2154
		mu 0 3 841 922 843
		f 3 -2360 -2908 -2148
		mu 0 3 839 931 841
		f 3 -2146 2980 2981
		mu 0 3 838 840 809
		f 3 -2362 -2361 -2144
		mu 0 3 837 930 839
		f 3 -2138 2982 -2363
		mu 0 3 837 835 929
		f 3 -2355 -2983 -2132
		mu 0 3 832 929 835
		f 3 -2366 -2354 -2124
		mu 0 3 831 928 832
		f 3 2983 -2369 -2122
		mu 0 3 829 933 831
		f 3 -2984 2984 2985
		mu 0 3 933 829 1112
		f 3 2986 -2986 2987
		mu 0 3 574 933 1112
		f 3 2988 2989 -2988
		mu 0 3 1112 578 574
		f 3 -2989 2990 2991
		mu 0 3 578 1112 827
		f 3 -2120 -2129 2992
		mu 0 3 828 830 834
		f 3 2993 2994 -2993
		mu 0 3 834 1113 828
		f 3 -2994 2995 2996
		mu 0 3 1113 834 819
		f 3 -2118 -2991 -2985
		mu 0 3 829 827 1112
		f 3 -2116 -2995 2997
		mu 0 3 824 828 1113
		f 3 -2104 -2998 2998
		mu 0 3 821 824 1113
		f 3 -2102 2999 -2108
		mu 0 3 823 822 826
		f 3 3000 -3000 3001
		mu 0 3 592 826 822
		f 3 -3001 3002 3003
		mu 0 3 826 592 586
		f 3 -2100 3004 3005
		mu 0 3 822 820 596
		f 3 3006 3007 -3005
		mu 0 3 820 1114 596
		f 3 -2098 -2999 -2997
		mu 0 3 819 821 1113
		f 3 -2096 3008 -3007
		mu 0 3 820 818 1114
		f 3 -3009 3009 3010
		mu 0 3 1114 818 1115
		f 3 3011 -3011 3012
		mu 0 3 599 1114 1115
		f 3 -2094 -2996 -2131
		mu 0 3 817 819 834
		f 3 -2092 3013 -3010
		mu 0 3 818 815 1115
		f 3 -2090 -2130 -2135
		mu 0 3 816 817 833
		f 3 3014 -2088 -2137
		mu 0 3 836 813 816
		f 3 3015 -3014 -2086
		mu 0 3 814 1115 815
		f 3 -3016 3016 3017
		mu 0 3 1115 814 601
		f 3 -3015 -2143 -2080
		mu 0 3 813 836 811
		f 3 -2074 -2142 -2982
		mu 0 3 809 811 838
		f 3 -2981 -2153 -2066
		mu 0 3 809 840 807
		f 3 -2152 -2159 -2062
		mu 0 3 807 842 806
		f 3 -2161 -2980 -2060
		mu 0 3 806 845 805
		f 3 -2064 -2056 -2072
		mu 0 3 808 804 803
		f 3 -2058 3018 -2051
		mu 0 3 802 805 800
		f 3 -2044 -3019 -2979
		mu 0 3 799 800 805
		f 3 -2175 -2043 -2977
		mu 0 3 850 798 799
		f 3 -2032 -2041 -2177
		mu 0 3 795 796 798
		f 3 -2030 -2179 -2187
		mu 0 3 794 795 852
		f 3 -2188 3019 -2029
		mu 0 3 794 856 792
		f 3 -2022 -3020 -2972
		mu 0 3 790 792 856
		f 3 -2020 3020 3021
		mu 0 3 791 789 642
		f 3 -2018 -2971 -2970
		mu 0 3 788 790 858
		f 3 -2966 -2012 -2969
		mu 0 3 860 787 788
		f 3 -2967 -2003 -2011
		mu 0 3 787 783 785
		f 3 3022 -2000 3023
		mu 0 3 1116 784 781
		f 3 -3023 3024 3025
		mu 0 3 784 1116 752
		f 3 -2204 -1999 -2968
		mu 0 3 862 782 783
		f 3 -2227 -1996 -2207
		mu 0 3 864 780 782
		f 3 -1994 3026 -3024
		mu 0 3 781 778 1116
		f 3 -1992 -2226 -2964
		mu 0 3 779 780 872
		f 3 -2236 3027 -1990
		mu 0 3 779 876 776
		f 3 -1988 3028 -3027
		mu 0 3 778 777 1116
		f 3 -3029 3029 3030
		mu 0 3 1116 777 754
		f 3 -1986 3031 3032
		mu 0 3 777 774 756
		f 3 -1984 -3028 -2962
		mu 0 3 775 776 876
		f 3 -2244 -2703 -1982
		mu 0 3 775 879 773
		f 3 -1980 3033 -3032
		mu 0 3 774 771 756
		f 3 -2702 -2707 -1979
		mu 0 3 773 1068 772
		f 3 -2706 -1968 -1977
		mu 0 3 772 769 770
		f 3 -2709 -1967 -2705
		mu 0 3 1066 768 769
		f 3 -1958 3034 3035
		mu 0 3 764 765 1117
		f 3 3036 3037 -3036
		mu 0 3 1117 735 764
		f 3 -1970 -1962 -1952
		mu 0 3 762 767 763
		f 3 -1948 -1957 3038
		mu 0 3 760 761 737
		f 3 -1950 -1938 -1973
		mu 0 3 762 758 757
		f 3 -3034 -1974 -1936
		mu 0 3 756 771 757
		f 3 -1934 -3030 -3033
		mu 0 3 756 754 777
		f 3 -1932 -1941 3039
		mu 0 3 753 755 759
		f 3 3040 3041 -3040
		mu 0 3 759 748 753
		f 3 -3031 -1930 -3025
		mu 0 3 1116 754 752
		f 3 -1926 -2004 -3026
		mu 0 3 752 751 784
		f 3 -1929 -3042 -1920
		mu 0 3 750 753 748
		f 3 -3041 -1945 -1913
		mu 0 3 748 759 747
		f 3 -1947 -1881 -1911
		mu 0 3 747 738 740
		f 3 -1879 3042 -1903
		mu 0 3 739 736 731
		f 3 -1877 -1946 -3039
		mu 0 3 737 738 760
		f 3 -1956 -3038 -1875
		mu 0 3 737 764 735
		f 3 -3037 3043 -1872
		mu 0 3 735 1117 734
		f 3 -1867 3044 3045
		mu 0 3 730 733 1118
		f 3 -1874 -1865 -3043
		mu 0 3 736 732 731
		f 3 -1863 -1901 -1904
		mu 0 3 731 728 742
		f 3 -1861 -3046 3046
		mu 0 3 729 730 1118
		f 3 -1902 -1858 -1845
		mu 0 3 722 728 723
		f 3 -1843 3047 -1900
		mu 0 3 722 703 743
		f 3 -1839 -1848 -1854
		mu 0 3 719 721 724
		f 3 -1837 3048 3049
		mu 0 3 720 717 706
		f 3 -1835 -1853 3050
		mu 0 3 718 719 726
		f 3 -1813 -1822 3051
		mu 0 3 708 710 714
		f 3 -1811 -3049 -1832
		mu 0 3 709 706 717
		f 3 3052 -1810 -3052
		mu 0 3 714 707 708
		f 3 -3053 3053 3054
		mu 0 3 707 714 693
		f 3 -1801 3055 -3050
		mu 0 3 706 704 720
		f 3 -1841 -3056 -1797
		mu 0 3 703 720 704
		f 3 -1891 -3048 -1795
		mu 0 3 702 743 703
		f 3 -1793 3056 -1894
		mu 0 3 702 699 657
		f 3 -1799 -1806 -1792
		mu 0 3 701 705 700
		f 3 -1783 3057 3058
		mu 0 3 698 696 667
		f 3 -1781 -1790 -1808
		mu 0 3 695 697 700
		f 3 -1779 3059 3060
		mu 0 3 696 694 669
		f 3 -1777 -1807 -3055
		mu 0 3 693 695 707
		f 3 -1775 3061 3062
		mu 0 3 694 692 671
		f 3 -1773 -3054 -1824
		mu 0 3 691 693 714
		f 3 -1771 3063 3064
		mu 0 3 692 690 673
		f 3 -1769 -1823 -1828
		mu 0 3 689 691 713
		f 3 -1767 3065 3066
		mu 0 3 690 688 675
		f 3 -3066 3067 3068
		mu 0 3 675 688 683
		f 3 -1765 -1827 3069
		mu 0 3 687 689 715
		f 3 -1759 3070 3071
		mu 0 3 685 686 1119
		f 3 3072 3073 -3072
		mu 0 3 1119 1120 685
		f 3 3074 -3074 3075
		mu 0 3 1121 685 1120
		f 3 -3076 3076 3077
		mu 0 3 1121 1120 1122
		f 3 -3077 3078 3079
		mu 0 3 1122 1120 1123
		f 3 -3080 3080 3081
		mu 0 3 1122 1123 1124
		f 3 -3081 3082 3083
		mu 0 3 1124 1123 1125
		f 3 -3084 3084 3085
		mu 0 3 1124 1125 1126
		f 3 3086 -3085 3087
		mu 0 3 1127 1126 1125
		f 3 3088 -3088 3089
		mu 0 3 1128 1127 1125
		f 3 3090 3091 -3090
		mu 0 3 1125 1129 1128
		f 3 -3089 3092 3093
		mu 0 3 1127 1128 1130
		f 3 3094 3095 -3094
		mu 0 3 1130 1131 1127
		f 3 3096 3097 -3096
		mu 0 3 1131 1132 1127
		f 3 -3095 3098 3099
		mu 0 3 1131 1130 1133
		f 3 -3087 -3098 3100
		mu 0 3 1126 1127 1132
		f 3 3101 -3101 3102
		mu 0 3 1134 1126 1132
		f 3 -3102 3103 3104
		mu 0 3 1126 1134 1135
		f 3 3105 3106 -3104
		mu 0 3 1134 1136 1135
		f 3 3107 3108 -3107
		mu 0 3 1136 1137 1135
		f 3 3109 -3109 3110
		mu 0 3 1138 1135 1137
		f 3 3111 3112 -3111
		mu 0 3 1137 1139 1138
		f 3 3113 -3113 3114
		mu 0 3 1140 1138 1139
		f 3 3115 3116 -3115
		mu 0 3 1139 1141 1140
		f 3 -3117 3117 3118
		mu 0 3 1140 1141 1142
		f 3 3119 3120 -3118
		mu 0 3 1141 1143 1142
		f 3 -3121 3121 3122
		mu 0 3 1142 1143 1144
		f 3 3123 3124 -3122
		mu 0 3 1143 1145 1144
		f 3 -3125 3125 3126
		mu 0 3 1144 1145 1146
		f 3 3127 3128 -3126
		mu 0 3 1145 1147 1146
		f 3 -3129 3129 3130
		mu 0 3 1146 1147 1148
		f 3 3131 -3130 3132
		mu 0 3 1149 1148 1147
		f 3 3133 -3133 3134
		mu 0 3 1150 1149 1147
		f 3 3135 3136 -3135
		mu 0 3 1147 1151 1150
		f 3 3137 3138 -3137
		mu 0 3 1151 1152 1150
		f 3 3139 3140 -3139
		mu 0 3 1152 621 1150
		f 3 3141 -3140 3142
		mu 0 3 1153 621 1152
		f 3 3143 3144 -3143
		mu 0 3 1152 1154 1153
		f 3 3145 3146 -3145
		mu 0 3 1154 1155 1153
		f 3 3147 3148 -3147
		mu 0 3 1155 1156 1153
		f 3 3149 3150 -3149
		mu 0 3 1156 620 1153
		f 3 -3150 3151 3152
		mu 0 3 620 1156 1157
		f 3 3153 3154 -3152
		mu 0 3 1156 1158 1157
		f 3 3155 3156 -3155
		mu 0 3 1158 1159 1157
		f 3 3157 3158 -3157
		mu 0 3 1159 1160 1157
		f 3 3159 -3159 3160
		mu 0 3 618 1157 1160
		f 3 -3158 3161 3162
		mu 0 3 1160 1159 1161
		f 3 3163 3164 -3163
		mu 0 3 1161 614 1160
		f 3 3165 -3164 3166
		mu 0 3 1162 614 1161
		f 3 3167 -3167 3168
		mu 0 3 1163 1162 1161
		f 3 3169 3170 -3168
		mu 0 3 1163 1164 1162
		f 3 3171 3172 -3171
		mu 0 3 1164 1165 1162
		f 3 3173 3174 -3173
		mu 0 3 1165 612 1162
		f 3 3175 3176 -3172
		mu 0 3 1164 1166 1165
		f 3 3177 3178 -3177
		mu 0 3 1166 606 1165
		f 3 3179 3180 -3176
		mu 0 3 1164 1167 1166
		f 3 3181 -3181 3182
		mu 0 3 1168 1166 1167
		f 3 3183 -3183 3184
		mu 0 3 1169 1168 1167
		f 3 3185 -3185 3186
		mu 0 3 1170 1169 1167
		f 3 -3187 3187 3188
		mu 0 3 1170 1167 1171
		f 3 3189 -3189 3190
		mu 0 3 1172 1170 1171
		f 3 -3191 3191 3192
		mu 0 3 1172 1171 1173
		f 3 3193 3194 -3192
		mu 0 3 1171 1163 1173
		f 3 3195 -3195 3196
		mu 0 3 1159 1173 1163
		f 3 3197 -3193 3198
		mu 0 3 1174 1172 1173
		f 3 3199 -3199 3200
		mu 0 3 1158 1174 1173
		f 3 -3200 3201 3202
		mu 0 3 1174 1158 1175
		f 3 3203 -3203 3204
		mu 0 3 1176 1174 1175
		f 3 3205 -3205 3206
		mu 0 3 1177 1176 1175
		f 3 3207 -3207 3208
		mu 0 3 1155 1177 1175
		f 3 -3208 3209 3210
		mu 0 3 1177 1155 1178
		f 3 3211 -3210 3212
		mu 0 3 1179 1178 1155
		f 3 3213 -3212 3214
		mu 0 3 1180 1178 1179
		f 3 3215 -3215 3216
		mu 0 3 1181 1180 1179
		f 3 -3217 3217 3218
		mu 0 3 1181 1179 1182
		f 3 3219 3220 -3219
		mu 0 3 1182 1183 1181
		f 3 3221 3222 -3221
		mu 0 3 1183 1184 1181
		f 3 3223 -3223 3224
		mu 0 3 1185 1181 1184
		f 3 3225 3226 -3225
		mu 0 3 1184 1186 1185
		f 3 3227 -3227 3228
		mu 0 3 1187 1185 1186
		f 3 -3228 3229 3230
		mu 0 3 1185 1187 1188
		f 3 3231 -3230 3232
		mu 0 3 1189 1188 1187
		f 3 -3232 3233 3234
		mu 0 3 1188 1189 1190
		f 3 3235 3236 -3235
		mu 0 3 1190 1191 1188
		f 3 -3237 3237 3238
		mu 0 3 1188 1191 1180
		f 3 -3236 3239 3240
		mu 0 3 1191 1190 1192
		f 3 3241 -3240 3242
		mu 0 3 1193 1192 1190
		f 3 3243 -3243 3244
		mu 0 3 1194 1193 1190
		f 3 3245 -3244 3246
		mu 0 3 1195 1193 1194
		f 3 -3246 3247 3248
		mu 0 3 1193 1195 1196
		f 3 3249 -3248 3250
		mu 0 3 1197 1196 1195
		f 3 -3250 3251 3252
		mu 0 3 1196 1197 1198
		f 3 3253 3254 -3253
		mu 0 3 1198 1199 1196
		f 3 -3255 3255 3256
		mu 0 3 1196 1199 1200
		f 3 3257 3258 -3256
		mu 0 3 1199 1176 1200
		f 3 -3258 3259 3260
		mu 0 3 1176 1199 1201
		f 3 3261 3262 -3260
		mu 0 3 1199 1202 1201
		f 3 3263 3264 -3263
		mu 0 3 1202 1203 1201
		f 3 3265 3266 -3265
		mu 0 3 1203 1172 1201
		f 3 3267 3268 -3264
		mu 0 3 1202 1204 1203
		f 3 3269 3270 -3269
		mu 0 3 1204 1205 1203
		f 3 3271 3272 -3271
		mu 0 3 1205 1170 1203
		f 3 3273 3274 -3270
		mu 0 3 1204 1206 1205
		f 3 3275 3276 -3275
		mu 0 3 1206 1207 1205
		f 3 3277 3278 -3277
		mu 0 3 1207 1169 1205;
	setAttr ".fc[2000:2499]"
		f 3 -3278 3279 3280
		mu 0 3 1169 1207 1208
		f 3 3281 -3280 3282
		mu 0 3 1209 1208 1207
		f 3 3283 -3283 3284
		mu 0 3 1210 1209 1207
		f 3 3285 3286 -3284
		mu 0 3 1210 1211 1209
		f 3 3287 -3287 3288
		mu 0 3 598 1209 1211
		f 3 3289 3290 -3286
		mu 0 3 1210 1212 1211
		f 3 3291 3292 -3291
		mu 0 3 1212 594 1211
		f 3 3293 3294 -3292
		mu 0 3 1212 1213 594
		f 3 3295 3296 -3295
		mu 0 3 1213 590 594
		f 3 -3294 3297 3298
		mu 0 3 1213 1212 1214
		f 3 3299 -3298 3300
		mu 0 3 1215 1214 1212
		f 3 -3300 3301 3302
		mu 0 3 1214 1215 1216
		f 3 3303 3304 -3302
		mu 0 3 1215 1217 1216
		f 3 3305 -3305 3306
		mu 0 3 1218 1216 1217
		f 3 3307 3308 -3307
		mu 0 3 1217 1219 1218
		f 3 3309 -3309 3310
		mu 0 3 1220 1218 1219
		f 3 3311 3312 -3311
		mu 0 3 1219 1198 1220
		f 3 3313 3314 -3312
		mu 0 3 1219 1202 1198
		f 3 3315 3316 -3308
		mu 0 3 1217 1204 1219
		f 3 3317 3318 -3304
		mu 0 3 1215 1206 1217
		f 3 -3318 3319 3320
		mu 0 3 1206 1215 1210
		f 3 -3290 -3320 -3301
		mu 0 3 1212 1210 1215
		f 3 -3282 3321 3322
		mu 0 3 1208 1209 600
		f 3 -3321 -3285 -3276
		mu 0 3 1206 1210 1207
		f 3 -3316 -3319 -3274
		mu 0 3 1204 1217 1206
		f 3 -3314 -3317 -3268
		mu 0 3 1202 1219 1204
		f 3 -3254 -3315 -3262
		mu 0 3 1199 1198 1202
		f 3 3323 -3313 -3252
		mu 0 3 1197 1220 1198
		f 3 -3249 -3257 3324
		mu 0 3 1193 1196 1200
		f 3 -3242 -3325 3325
		mu 0 3 1192 1193 1200
		f 3 3326 3327 -3326
		mu 0 3 1200 1177 1192
		f 3 -3241 3328 3329
		mu 0 3 1191 1192 1178
		f 3 3330 -3245 -3234
		mu 0 3 1189 1194 1190
		f 3 -3231 -3239 3331
		mu 0 3 1185 1188 1180
		f 3 -3226 3332 3333
		mu 0 3 1186 1184 1221
		f 3 3334 -3333 3335
		mu 0 3 1222 1221 1184
		f 3 -3335 3336 3337
		mu 0 3 1221 1222 1223
		f 3 3338 -3337 3339
		mu 0 3 1224 1223 1222
		f 3 3340 -3340 3341
		mu 0 3 1183 1224 1222
		f 3 -3341 3342 3343
		mu 0 3 1224 1183 1225
		f 3 3344 -3343 3345
		mu 0 3 1226 1225 1183
		f 3 -3345 3346 3347
		mu 0 3 1225 1226 1141
		f 3 3348 3349 -3344
		mu 0 3 1225 1227 1224
		f 3 3350 -3350 3351
		mu 0 3 1228 1224 1227
		f 3 3352 -3352 3353
		mu 0 3 1229 1228 1227
		f 3 3354 -3354 3355
		mu 0 3 1137 1229 1227
		f 3 -3349 3356 3357
		mu 0 3 1227 1225 1139
		f 3 -3339 -3351 3358
		mu 0 3 1223 1224 1228
		f 3 -3222 -3342 -3336
		mu 0 3 1184 1183 1222
		f 3 -3220 3359 -3346
		mu 0 3 1183 1182 1226
		f 3 3360 -3360 3361
		mu 0 3 1230 1226 1182
		f 3 3362 3363 -3362
		mu 0 3 1182 1154 1230
		f 3 -3361 3364 3365
		mu 0 3 1226 1230 1231
		f 3 3366 3367 -3365
		mu 0 3 1230 1151 1231
		f 3 3368 -3368 3369
		mu 0 3 1145 1231 1151
		f 3 3370 -3366 3371
		mu 0 3 1143 1226 1231
		f 3 -3363 -3218 3372
		mu 0 3 1154 1182 1179
		f 3 -3224 -3332 -3216
		mu 0 3 1181 1185 1180
		f 3 -3214 -3238 -3330
		mu 0 3 1178 1180 1191
		f 3 -3328 -3211 -3329
		mu 0 3 1192 1177 1178
		f 3 -3327 -3259 -3206
		mu 0 3 1177 1200 1176
		f 3 3373 -3204 -3261
		mu 0 3 1201 1174 1176
		f 3 -3374 -3267 -3198
		mu 0 3 1174 1201 1172
		f 3 -3266 -3273 -3190
		mu 0 3 1172 1203 1170
		f 3 -3272 -3279 -3186
		mu 0 3 1170 1205 1169
		f 3 -3281 3374 -3184
		mu 0 3 1169 1208 1168
		f 3 3375 3376 -3375
		mu 0 3 1208 602 1168
		f 3 -3182 3377 3378
		mu 0 3 1166 1168 604
		f 3 -3180 3379 -3188
		mu 0 3 1167 1164 1171
		f 3 -3194 -3380 -3170
		mu 0 3 1163 1171 1164
		f 3 -3197 -3169 -3162
		mu 0 3 1159 1163 1161
		f 3 -3196 -3156 -3201
		mu 0 3 1173 1159 1158
		f 3 3380 -3202 -3154
		mu 0 3 1156 1175 1158
		f 3 -3381 -3148 -3209
		mu 0 3 1175 1156 1155
		f 3 -3213 -3146 -3373
		mu 0 3 1179 1155 1154
		f 3 -3144 3381 -3364
		mu 0 3 1154 1152 1230
		f 3 -3367 -3382 -3138
		mu 0 3 1151 1230 1152
		f 3 -3134 3382 3383
		mu 0 3 1149 1150 622
		f 3 3384 -3132 3385
		mu 0 3 1232 1148 1149
		f 3 3386 3387 -3386
		mu 0 3 1149 624 1232
		f 3 3388 -3388 3389
		mu 0 3 1233 1232 624
		f 3 -3389 3390 3391
		mu 0 3 1232 1233 1234
		f 3 3392 -3391 3393
		mu 0 3 1235 1234 1233
		f 3 3394 3395 -3394
		mu 0 3 1233 1236 1235
		f 3 3396 -3396 3397
		mu 0 3 1237 1235 1236
		f 3 3398 3399 -3398
		mu 0 3 1236 1238 1237
		f 3 3400 -3400 3401
		mu 0 3 1239 1237 1238
		f 3 3402 3403 -3402
		mu 0 3 1238 635 1239
		f 3 3404 -3404 3405
		mu 0 3 640 1239 635
		f 3 -3405 3406 3407
		mu 0 3 1239 640 663
		f 3 -3401 3408 3409
		mu 0 3 1237 1239 664
		f 3 -3399 3410 3411
		mu 0 3 1238 1236 627
		f 3 3412 3413 -3412
		mu 0 3 627 634 1238
		f 3 -3397 3414 3415
		mu 0 3 1235 1237 666
		f 3 -3395 3416 3417
		mu 0 3 1236 1233 625
		f 3 -3393 3418 3419
		mu 0 3 1234 1235 668
		f 3 3420 3421 -3392
		mu 0 3 1234 1240 1232
		f 3 -3421 3422 3423
		mu 0 3 1240 1234 670
		f 3 -3385 -3422 3424
		mu 0 3 1148 1232 1240
		f 3 3425 3426 -3425
		mu 0 3 1240 1241 1148
		f 3 -3426 3427 3428
		mu 0 3 1241 1240 672
		f 3 3429 -3131 -3427
		mu 0 3 1241 1146 1148
		f 3 -3430 3430 3431
		mu 0 3 1146 1241 677
		f 3 -3136 -3128 -3370
		mu 0 3 1151 1147 1145
		f 3 3432 -3127 -3432
		mu 0 3 677 1144 1146
		f 3 -3369 -3124 -3372
		mu 0 3 1231 1145 1143
		f 3 3433 -3123 3434
		mu 0 3 678 1142 1144
		f 3 -3371 -3120 -3347
		mu 0 3 1226 1143 1141
		f 3 3435 -3119 3436
		mu 0 3 680 1140 1142
		f 3 -3436 3437 3438
		mu 0 3 1140 680 1242
		f 3 -3116 -3357 -3348
		mu 0 3 1141 1139 1225
		f 3 -3114 -3439 3439
		mu 0 3 1138 1140 1242
		f 3 3440 3441 -3440
		mu 0 3 1242 1243 1138
		f 3 -3441 3442 3443
		mu 0 3 1243 1242 1244
		f 3 -3443 3444 3445
		mu 0 3 1244 1242 681
		f 3 3446 -3446 3447
		mu 0 3 1121 1244 681
		f 3 3448 -3444 3449
		mu 0 3 1122 1243 1244
		f 3 -3112 -3356 -3358
		mu 0 3 1139 1137 1227
		f 3 -3110 -3442 3450
		mu 0 3 1135 1138 1243
		f 3 3451 -3451 3452
		mu 0 3 1124 1135 1243
		f 3 -3355 -3108 3453
		mu 0 3 1229 1137 1136
		f 3 -3452 -3086 -3105
		mu 0 3 1135 1124 1126
		f 3 -3091 -3083 3454
		mu 0 3 1129 1125 1123
		f 3 3455 3456 -3455
		mu 0 3 1123 1245 1129
		f 3 -3449 -3082 -3453
		mu 0 3 1243 1122 1124
		f 3 -3456 -3079 3457
		mu 0 3 1245 1123 1120
		f 3 -3447 -3078 -3450
		mu 0 3 1244 1121 1122
		f 3 -3073 3458 -3458
		mu 0 3 1120 1119 1245
		f 3 -1757 -3075 3459
		mu 0 3 682 685 1121
		f 3 -1755 -3068 -1763
		mu 0 3 684 683 688
		f 3 -1751 -3460 -3448
		mu 0 3 681 682 1121
		f 3 -3438 -1749 -3445
		mu 0 3 1242 680 681
		f 3 -3434 -1748 -3437
		mu 0 3 1142 678 680
		f 3 -1753 -1745 3460
		mu 0 3 683 679 676
		f 3 -3433 -1744 -3435
		mu 0 3 1144 677 678
		f 3 3461 -1741 -3431
		mu 0 3 1241 674 677
		f 3 -1739 -3069 -3461
		mu 0 3 676 675 683
		f 3 -1737 -3064 -3067
		mu 0 3 675 673 690
		f 3 -1735 -3462 -3429
		mu 0 3 672 674 1241
		f 3 -1733 -3062 -3065
		mu 0 3 673 671 692
		f 3 -1731 -3428 -3424
		mu 0 3 670 672 1240
		f 3 -1729 -3060 -3063
		mu 0 3 671 669 694
		f 3 -1727 -3423 -3420
		mu 0 3 668 670 1234
		f 3 -1725 -3058 -3061
		mu 0 3 669 667 696
		f 3 -1723 -3419 -3416
		mu 0 3 666 668 1235
		f 3 -1721 3462 -3059
		mu 0 3 667 665 698
		f 3 3463 -3463 3464
		mu 0 3 659 698 665
		f 3 -1719 -3415 -3410
		mu 0 3 664 666 1237
		f 3 -1715 -3409 -3408
		mu 0 3 663 664 1239
		f 3 -1717 -1703 -3465
		mu 0 3 665 661 659
		f 3 -3464 -1699 -1786
		mu 0 3 698 659 658
		f 3 -1695 -3057 -1787
		mu 0 3 658 657 699
		f 3 -1893 -1693 -1898
		mu 0 3 744 657 655
		f 3 -1897 -1689 -1907
		mu 0 3 745 655 654
		f 3 -1916 -1908 -1687
		mu 0 3 653 746 654
		f 3 -1683 -1692 -1698
		mu 0 3 651 652 656
		f 3 -1681 -1702 -1710
		mu 0 3 649 651 660
		f 3 -1685 -1679 -1919
		mu 0 3 653 650 648
		f 3 -1918 -1675 -1923
		mu 0 3 749 648 647
		f 3 -2006 -1924 -1673
		mu 0 3 646 751 647
		f 3 -1671 -2016 -2009
		mu 0 3 646 644 786
		f 3 -1669 -1678 -1709
		mu 0 3 643 645 649
		f 3 -2017 -1667 -3021
		mu 0 3 789 644 642
		f 3 -1665 -1708 -1714
		mu 0 3 641 643 662
		f 3 -1663 3465 -3022
		mu 0 3 642 639 791
		f 3 -1713 -3407 -1662
		mu 0 3 641 663 640
		f 3 -2025 -3466 -1657
		mu 0 3 638 791 639
		f 3 -2034 -2027 -1655
		mu 0 3 637 793 638
		f 3 -1651 -1660 -3406
		mu 0 3 635 636 640
		f 3 -3403 -3414 -1650
		mu 0 3 635 1238 634
		f 3 -1653 -1645 -2036
		mu 0 3 637 633 632
		f 3 -2039 -1643 -2046
		mu 0 3 797 632 631
		f 3 -1641 3466 -2049
		mu 0 3 631 629 801
		f 3 3467 3468 -3467
		mu 0 3 629 611 801
		f 3 -1639 -1648 3469
		mu 0 3 628 630 634
		f 3 -3413 -1633 -3470
		mu 0 3 634 627 628
		f 3 -1631 -3411 -3418
		mu 0 3 625 627 1236
		f 3 -1629 3470 3471
		mu 0 3 626 623 617
		f 3 -1627 -3417 -3390
		mu 0 3 624 625 1233
		f 3 -3387 -3384 -1626
		mu 0 3 624 1149 622
		f 3 -3141 -1622 -3383
		mu 0 3 1150 621 622
		f 3 -3142 -3151 -1619
		mu 0 3 621 1153 620
		f 3 -3160 -1617 -3153
		mu 0 3 1157 618 620
		f 3 -1615 -3471 -1624
		mu 0 3 619 617 623
		f 3 -1613 -3161 3472
		mu 0 3 616 618 1160
		f 3 -1611 -1636 -3472
		mu 0 3 617 615 626
		f 3 -1610 -3473 -3165
		mu 0 3 614 616 1160
		f 3 3473 -1638 -1607
		mu 0 3 613 629 615
		f 3 -3166 -3175 -1606
		mu 0 3 614 1162 612
		f 3 -3468 -3474 -1603
		mu 0 3 611 629 613
		f 3 -3174 3474 -1602
		mu 0 3 612 1165 609
		f 3 -2052 -3469 -1599
		mu 0 3 610 801 611
		f 3 -2055 -1597 3475
		mu 0 3 803 610 608
		f 3 -1595 -3475 -3179
		mu 0 3 606 609 1165
		f 3 -2073 -3476 -1593
		mu 0 3 607 803 608
		f 3 -2071 -1591 -2078
		mu 0 3 810 607 605
		f 3 -3379 -1590 -3178
		mu 0 3 1166 604 606
		f 3 -2085 -2079 -1587
		mu 0 3 603 812 605
		f 3 -1585 -3378 -3377
		mu 0 3 602 604 1168
		f 3 -1583 -3017 -2084
		mu 0 3 603 601 814
		f 3 -3323 -1582 -3376
		mu 0 3 1208 600 602
		f 3 -3013 -3018 -1579
		mu 0 3 599 1115 601
		f 3 -1577 -3322 -3288
		mu 0 3 598 600 1209
		f 3 -1575 3476 -3012
		mu 0 3 599 597 1114
		f 3 -1573 -3289 3477
		mu 0 3 595 598 1211
		f 3 -1571 -3008 -3477
		mu 0 3 597 596 1114
		f 3 -3006 -1569 3478
		mu 0 3 822 596 593
		f 3 -3478 -3293 -1568
		mu 0 3 595 1211 594
		f 3 -3002 -3479 -1563
		mu 0 3 592 822 593
		f 3 -1566 -3297 -1560
		mu 0 3 591 594 590
		f 3 -1555 3479 3480
		mu 0 3 587 589 1246
		f 3 3481 -3481 3482
		mu 0 3 1247 587 1246
		f 3 3483 -3483 3484
		mu 0 3 1248 1247 1246
		f 3 3485 3486 -3484
		mu 0 3 1248 1249 1247
		f 3 3487 -3487 3488
		mu 0 3 1250 1247 1249
		f 3 3489 -3489 3490
		mu 0 3 1251 1250 1249
		f 3 3491 -3491 3492
		mu 0 3 1252 1251 1249
		f 3 -3493 3493 3494
		mu 0 3 1252 1249 1253
		f 3 3495 -3495 3496
		mu 0 3 1254 1252 1253
		f 3 3497 3498 -3490
		mu 0 3 1251 1255 1250
		f 3 3499 3500 -3499
		mu 0 3 1255 583 1250
		f 3 -3488 3501 3502
		mu 0 3 1247 1250 585
		f 3 -3486 3503 -3494
		mu 0 3 1249 1248 1253
		f 3 -1553 -3003 -1561
		mu 0 3 588 586 592
		f 3 -3503 -1552 -3482
		mu 0 3 1247 585 587
		f 3 -2110 -3004 -1549
		mu 0 3 584 826 586
		f 3 -1547 -3502 -3501
		mu 0 3 583 585 1250
		f 3 -1545 3504 -2111
		mu 0 3 584 580 825
		f 3 3505 -1544 -3500
		mu 0 3 1255 582 583
		f 3 -1537 -2112 -3505
		mu 0 3 580 579 825
		f 3 -2114 -1535 -2992
		mu 0 3 827 579 578
		f 3 -1539 3506 -1531
		mu 0 3 577 581 576
		f 3 -1529 3507 3508
		mu 0 3 573 576 1256
		f 3 -1527 -2990 -1534
		mu 0 3 575 574 578
		f 3 -2987 -1525 -2903
		mu 0 3 933 574 572
		f 3 3509 -1524 -3509
		mu 0 3 1256 571 573
		f 3 -3510 3510 3511
		mu 0 3 571 1256 1257
		f 3 -2902 -1521 -2901
		mu 0 3 934 572 570
		f 3 3512 -1519 -3512
		mu 0 3 1257 568 571
		f 3 -2900 -1517 -2894
		mu 0 3 936 570 569
		f 3 -3513 3513 -1514
		mu 0 3 568 1257 567
		f 3 -1507 -2892 -1515
		mu 0 3 565 564 569
		f 3 -2889 -1505 -2887
		mu 0 3 941 564 563
		f 3 -1509 3514 -1502
		mu 0 3 562 566 561
		f 3 -1495 -2885 -1504
		mu 0 3 559 558 563
		f 3 -2882 -1493 -2495
		mu 0 3 946 558 557
		f 3 -1497 3515 -1490
		mu 0 3 556 560 555
		f 3 -1483 -2493 -1492
		mu 0 3 553 552 557
		f 3 -2490 -1481 -2843
		mu 0 3 984 552 551
		f 3 -1485 3516 -1478
		mu 0 3 550 554 549
		f 3 -1473 3517 3518
		mu 0 3 546 548 1258
		f 3 3519 3520 -3519
		mu 0 3 1258 1259 546
		f 3 -3520 3521 3522
		mu 0 3 1259 1258 1260
		f 3 3523 3524 -3523
		mu 0 3 1260 526 1259
		f 3 3525 -3525 3526
		mu 0 3 542 1259 526
		f 3 -1471 -2844 -1480
		mu 0 3 547 545 551
		f 3 -1469 -3521 3527
		mu 0 3 543 546 1259
		f 3 -1467 -2500 -2845
		mu 0 3 545 544 986
		f 3 -2502 -1465 3528
		mu 0 3 988 544 541
		f 3 -3526 -1463 -3528
		mu 0 3 1259 542 543
		f 3 -1461 3529 3530
		mu 0 3 540 542 527
		f 3 -1459 -2839 -3529
		mu 0 3 541 539 988
		f 3 -1457 3531 3532
		mu 0 3 537 540 529
		f 3 -1455 -2835 -2840
		mu 0 3 539 538 990
		f 3 -2828 -1453 -2821
		mu 0 3 1097 538 536
		f 3 -1432 -1452 -3533
		mu 0 3 529 531 537
		f 3 -1430 3533 -1437
		mu 0 3 530 528 533
		f 3 3534 -3534 3535
		mu 0 3 522 533 528
		f 3 -1428 -3532 -3531
		mu 0 3 527 529 540
		f 3 -1424 -3530 -3527
		mu 0 3 526 527 542
		f 3 -3524 3536 -1423
		mu 0 3 526 1260 525
		f 3 -1426 -1418 -3536
		mu 0 3 528 524 522
		f 3 -1414 3537 -3535
		mu 0 3 522 518 533
		f 3 -1406 -1439 -3538
		mu 0 3 518 517 533
		f 3 -1404 3538 -1440
		mu 0 3 517 513 534
		f 3 -1402 -1409 3539
		mu 0 3 515 516 519
		f 3 3540 -1399 -2780
		mu 0 3 1089 512 514
		f 3 -1396 -1445 -3539
		mu 0 3 513 511 534
		f 3 -1394 -3541 3541
		mu 0 3 506 512 1089
		f 3 -1444 -1392 -1448
		mu 0 3 535 511 510
		f 3 -2820 -1449 -1390
		mu 0 3 509 536 510
		f 3 -1388 -2555 -2819
		mu 0 3 509 508 1011
		f 3 -1386 -2805 -2552
		mu 0 3 508 507 1010
		f 3 -1385 -3542 -2783
		mu 0 3 507 506 1089
		f 3 3542 3543 3544
		mu 0 3 1261 1262 1263
		f 3 3545 3546 -3544
		mu 0 3 1262 1264 1263
		f 3 3547 3548 -3547
		mu 0 3 1264 1265 1263
		f 3 -3548 3549 3550
		mu 0 3 1265 1264 1266
		f 3 3551 3552 -3551
		mu 0 3 1266 1267 1265
		f 3 3553 -3553 3554
		mu 0 3 1268 1265 1267
		f 3 3555 -3555 3556
		mu 0 3 1269 1268 1267
		f 3 3557 3558 -3557
		mu 0 3 1267 1270 1269
		f 3 3559 3560 -3559
		mu 0 3 1270 1271 1269
		f 3 -3561 3561 3562
		mu 0 3 1269 1271 1272
		f 3 -3562 3563 3564
		mu 0 3 1272 1271 1273
		f 3 3565 -3564 3566
		mu 0 3 1274 1273 1271
		f 3 3567 3568 -3567
		mu 0 3 1271 1275 1274
		f 3 3569 -3569 3570
		mu 0 3 1276 1274 1275
		f 3 3571 -3571 3572
		mu 0 3 1277 1276 1275
		f 3 3573 3574 -3573
		mu 0 3 1275 1278 1277
		f 3 3575 -3575 3576
		mu 0 3 1279 1277 1278
		f 3 3577 3578 -3577
		mu 0 3 1278 1280 1279
		f 3 3579 -3579 3580
		mu 0 3 1281 1279 1280
		f 3 3581 3582 -3581
		mu 0 3 1280 1282 1281
		f 3 -3582 3583 3584
		mu 0 3 1282 1280 1283
		f 3 3585 -3584 3586
		mu 0 3 1284 1283 1280
		f 3 -3586 3587 3588
		mu 0 3 1283 1284 1285
		f 3 -3588 3589 3590
		mu 0 3 1285 1284 1270
		f 3 3591 3592 -3590
		mu 0 3 1284 1286 1270
		f 3 -3592 3593 3594
		mu 0 3 1286 1284 1278
		f 3 3595 -3589 3596
		mu 0 3 1287 1283 1285
		f 3 3597 3598 -3597
		mu 0 3 1285 1266 1287
		f 3 3599 -3599 3600
		mu 0 3 1288 1287 1266
		f 3 3601 -3600 3602
		mu 0 3 1289 1287 1288
		f 3 3603 3604 -3603
		mu 0 3 1288 1290 1289
		f 3 -3604 3605 3606
		mu 0 3 1290 1288 1291
		f 3 3607 -3606 3608
		mu 0 3 1264 1291 1288
		f 3 -3608 3609 3610
		mu 0 3 1291 1264 1292
		f 3 3611 -3611 3612
		mu 0 3 1293 1291 1292
		f 3 3613 3614 -3613
		mu 0 3 1292 1294 1293
		f 3 3615 3616 -3615
		mu 0 3 1294 1295 1293
		f 3 3617 3618 -3617
		mu 0 3 1295 1296 1293
		f 3 3619 3620 -3619
		mu 0 3 1296 1297 1293
		f 3 3621 3622 -3621
		mu 0 3 1297 1298 1293
		f 3 3623 3624 -3622
		mu 0 3 1297 1299 1298
		f 3 -3625 3625 3626
		mu 0 3 1298 1299 1290
		f 3 3627 -3624 3628
		mu 0 3 1300 1299 1297
		f 3 3629 3630 -3629
		mu 0 3 1297 1301 1300
		f 3 -3620 3631 -3630
		mu 0 3 1297 1296 1301
		f 3 3632 -3632 3633
		mu 0 3 1302 1301 1296
		f 3 -3633 3634 3635
		mu 0 3 1301 1302 1303
		f 3 3636 -3635 3637
		mu 0 3 1304 1303 1302
		f 3 3638 -3638 3639
		mu 0 3 1305 1304 1302
		f 3 3640 3641 -3640
		mu 0 3 1302 1295 1305
		f 3 -3642 3642 3643
		mu 0 3 1305 1295 1306
		f 3 3644 -3643 3645
		mu 0 3 1307 1306 1295
		f 3 -3645 3646 3647
		mu 0 3 1306 1307 1308
		f 3 3648 3649 -3648
		mu 0 3 1308 1309 1306
		f 3 -3649 3650 3651
		mu 0 3 1309 1308 1310
		f 3 3652 3653 -3651
		mu 0 3 1308 1311 1310
		f 3 3654 3655 -3654
		mu 0 3 1311 1312 1310
		f 3 3656 -3656 3657
		mu 0 3 1313 1310 1312
		f 3 -3658 3658 3659
		mu 0 3 1313 1312 1314
		f 3 3660 -3660 3661
		mu 0 3 1315 1313 1314
		f 3 3662 3663 -3662
		mu 0 3 1314 1316 1315
		f 3 3664 3665 -3664
		mu 0 3 1316 1317 1315
		f 3 -3666 3666 3667
		mu 0 3 1315 1317 1318
		f 3 -3668 3668 3669
		mu 0 3 1315 1318 1319
		f 3 3670 -3669 3671
		mu 0 3 1320 1319 1318
		f 3 3672 -3672 3673
		mu 0 3 1321 1320 1318
		f 3 3674 3675 -3674
		mu 0 3 1318 1322 1321
		f 3 -3673 3676 3677
		mu 0 3 1320 1321 1323
		f 3 3678 3679 -3678
		mu 0 3 1323 1324 1320
		f 3 3680 3681 -3680
		mu 0 3 1324 1325 1320
		f 3 3682 3683 -3681
		mu 0 3 1324 1305 1325
		f 3 3684 3685 -3684
		mu 0 3 1305 1309 1325
		f 3 -3686 3686 3687
		mu 0 3 1325 1309 1319
		f 3 -3687 3688 3689
		mu 0 3 1319 1309 1313
		f 3 -3679 3690 3691
		mu 0 3 1324 1323 1326
		f 3 3692 3693 -3692
		mu 0 3 1326 1304 1324
		f 3 -3693 3694 3695
		mu 0 3 1304 1326 1327
		f 3 -3688 -3671 -3682
		mu 0 3 1325 1319 1320
		f 3 -3675 -3667 3696
		mu 0 3 1322 1318 1317
		f 3 3697 3698 -3697
		mu 0 3 1317 1328 1322
		f 3 -3698 3699 3700
		mu 0 3 1328 1317 1329
		f 3 3701 3702 -3701
		mu 0 3 1329 1330 1328
		f 3 -3702 3703 3704
		mu 0 3 1330 1329 1331
		f 3 3705 -3704 3706
		mu 0 3 1332 1331 1329
		f 3 -3707 3707 3708
		mu 0 3 1332 1329 1316
		f 3 3709 -3709 3710
		mu 0 3 1333 1332 1316
		f 3 -3710 3711 3712
		mu 0 3 1332 1333 1334
		f 3 3713 -3712 3714
		mu 0 3 1335 1334 1333
		f 3 -3715 3715 3716
		mu 0 3 1335 1333 1336
		f 3 3717 -3717 3718
		mu 0 3 1337 1335 1336
		f 3 -3719 3719 3720
		mu 0 3 1337 1336 1338
		f 3 3721 -3721 3722
		mu 0 3 1339 1337 1338
		f 3 3723 3724 -3723
		mu 0 3 1338 1340 1339
		f 3 3725 3726 -3725
		mu 0 3 1340 1341 1339
		f 3 -3727 3727 3728
		mu 0 3 1339 1341 1342
		f 3 3729 -3728 3730
		mu 0 3 1343 1342 1341
		f 3 3731 3732 -3731
		mu 0 3 1341 1344 1343
		f 3 3733 -3733 3734
		mu 0 3 1345 1343 1344
		f 3 3735 -3735 3736
		mu 0 3 1346 1345 1344
		f 3 3737 -3737 3738
		mu 0 3 1347 1346 1344
		f 3 3739 -3739 3740
		mu 0 3 1348 1347 1344
		f 3 3741 3742 -3740
		mu 0 3 1348 1349 1347
		f 3 -3743 3743 3744
		mu 0 3 1347 1349 1350
		f 3 -3745 3745 3746
		mu 0 3 1347 1350 1272
		f 3 3747 -3744 3748
		mu 0 3 1351 1350 1349
		f 3 3749 3750 -3749
		mu 0 3 1349 1352 1351
		f 3 3751 -3751 3752
		mu 0 3 1307 1351 1352
		f 3 3753 -3753 3754
		mu 0 3 1353 1307 1352
		f 3 -3755 3755 3756
		mu 0 3 1353 1352 1354
		f 3 -3757 3757 3758
		mu 0 3 1353 1354 1340
		f 3 3759 -3759 3760
		mu 0 3 1311 1353 1340
		f 3 3761 -3752 3762
		mu 0 3 1294 1351 1307
		f 3 -3762 3763 3764
		mu 0 3 1351 1294 1262
		f 3 -3750 3765 -3756
		mu 0 3 1352 1349 1354
		f 3 3766 -3748 3767
		mu 0 3 1261 1350 1351
		f 3 -3767 3768 3769
		mu 0 3 1350 1261 1268
		f 3 -3742 3770 -3766
		mu 0 3 1349 1348 1354
		f 3 3771 -3771 3772
		mu 0 3 1341 1354 1348
		f 3 3773 3774 -3738
		mu 0 3 1347 1273 1346
		f 3 3775 -3775 3776
		mu 0 3 1355 1346 1273
		f 3 -3777 3777 3778
		mu 0 3 1355 1273 1356
		f 3 3779 3780 -3779
		mu 0 3 1356 1357 1355
		f 3 3781 -3781 3782
		mu 0 3 1345 1355 1357
		f 3 -3783 3783 3784
		mu 0 3 1345 1357 1358
		f 3 -3784 3785 3786
		mu 0 3 1358 1357 1359
		f 3 3787 3788 -3786
		mu 0 3 1357 1360 1359
		f 3 3789 3790 -3789
		mu 0 3 1360 1361 1359
		f 3 3791 -3791 3792
		mu 0 3 1362 1359 1361
		f 3 3793 -3793 3794
		mu 0 3 1363 1362 1361
		f 3 3795 3796 -3795
		mu 0 3 1361 1364 1363
		f 3 -3797 3797 3798
		mu 0 3 1363 1364 1365
		f 3 3799 3800 -3798
		mu 0 3 1364 1366 1365
		f 3 3801 -3801 3802
		mu 0 3 1367 1365 1366
		f 3 3803 -3803 3804
		mu 0 3 1368 1367 1366
		f 3 3805 3806 -3805
		mu 0 3 1366 1369 1368
		f 3 3807 3808 -3807
		mu 0 3 1369 1370 1368
		f 3 3809 -3809 3810
		mu 0 3 1371 1368 1370
		f 3 3811 -3811 3812
		mu 0 3 1372 1371 1370
		f 3 3813 3814 -3813
		mu 0 3 1370 1373 1372
		f 3 3815 -3815 3816
		mu 0 3 1374 1372 1373
		f 3 3817 3818 -3817
		mu 0 3 1373 1375 1374
		f 3 3819 -3819 3820
		mu 0 3 1376 1374 1375
		f 3 3821 3822 -3821
		mu 0 3 1375 1377 1376
		f 3 -3822 3823 3824
		mu 0 3 1377 1375 1378
		f 3 3825 -3824 3826
		mu 0 3 1379 1378 1375
		f 3 -3826 3827 3828
		mu 0 3 1378 1379 1380
		f 3 3829 3830 -3829
		mu 0 3 1380 1381 1378
		f 3 3831 -3831 3832
		mu 0 3 1382 1378 1381
		f 3 3833 3834 -3833
		mu 0 3 1381 1383 1382
		f 3 -3834 3835 3836
		mu 0 3 1383 1381 1384
		f 3 3837 -3836 3838
		mu 0 3 1385 1384 1381
		f 3 -3838 3839 3840
		mu 0 3 1384 1385 1277
		f 3 3841 3842 -3837
		mu 0 3 1384 1386 1383
		f 3 -3842 3843 3844
		mu 0 3 1386 1384 1279
		f 3 -3830 3845 -3839
		mu 0 3 1381 1380 1385
		f 3 3846 -3846 3847
		mu 0 3 1387 1385 1380
		f 3 3848 3849 -3848
		mu 0 3 1380 1388 1387
		f 3 3850 3851 -3850
		mu 0 3 1388 1389 1387
		f 3 3852 -3852 3853
		mu 0 3 1390 1387 1389
		f 3 -3854 3854 3855
		mu 0 3 1390 1389 1391
		f 3 -3855 3856 3857
		mu 0 3 1391 1389 1392
		f 3 3858 3859 -3857
		mu 0 3 1389 1393 1392
		f 3 -3860 3860 3861
		mu 0 3 1392 1393 1394
		f 3 3862 3863 -3862
		mu 0 3 1394 1360 1392
		f 3 -3863 3864 3865
		mu 0 3 1360 1394 1395
		f 3 3866 -3865 3867
		mu 0 3 1396 1395 1394
		f 3 3868 3869 -3868
		mu 0 3 1394 1369 1396
		f 3 -3867 3870 3871
		mu 0 3 1395 1396 1364
		f 3 3872 -3869 -3861
		mu 0 3 1393 1369 1394
		f 3 3873 3874 -3873
		mu 0 3 1393 1397 1369
		f 3 -3874 3875 3876
		mu 0 3 1397 1393 1388
		f 3 3877 -3877 3878
		mu 0 3 1379 1397 1388
		f 3 -3878 3879 3880
		mu 0 3 1397 1379 1373
		f 3 3881 3882 -3858
		mu 0 3 1392 1357 1391
		f 3 3883 -3856 3884
		mu 0 3 1356 1390 1391
		f 3 3885 -3884 3886
		mu 0 3 1274 1390 1356
		f 3 -3853 3887 3888
		mu 0 3 1387 1390 1276
		f 3 -3851 -3876 -3859
		mu 0 3 1389 1388 1393
		f 3 -3847 -3889 3889
		mu 0 3 1385 1387 1276
		f 3 -3849 -3828 -3879
		mu 0 3 1388 1380 1379
		f 3 -3832 3890 -3825
		mu 0 3 1378 1382 1377
		f 3 -3820 3891 3892
		mu 0 3 1374 1376 1398
		f 3 3893 3894 -3893
		mu 0 3 1398 1399 1374
		f 3 -3894 3895 3896
		mu 0 3 1399 1398 1400
		f 3 3897 3898 -3897
		mu 0 3 1400 1401 1399
		f 3 3899 -3899 3900
		mu 0 3 1402 1399 1401
		f 3 3901 3902 -3901
		mu 0 3 1401 1403 1402
		f 3 3903 -3903 3904
		mu 0 3 1404 1402 1403
		f 3 3905 3906 -3905
		mu 0 3 1403 1405 1404
		f 3 3907 3908 -3907
		mu 0 3 1405 1406 1404
		f 3 3909 -3909 3910
		mu 0 3 1407 1404 1406
		f 3 3911 -3911 3912
		mu 0 3 1367 1407 1406
		f 3 -3913 3913 3914
		mu 0 3 1367 1406 1408
		f 3 3915 3916 -3915
		mu 0 3 1408 1409 1367
		f 3 -3916 3917 3918
		mu 0 3 1409 1408 1410
		f 3 3919 -3919 3920
		mu 0 3 1411 1409 1410
		f 3 -3921 3921 3922
		mu 0 3 1411 1410 1412
		f 3 -3922 3923 3924
		mu 0 3 1412 1410 1413
		f 3 3925 3926 -3924
		mu 0 3 1410 1414 1413
		f 3 3927 -3927 3928
		mu 0 3 1415 1413 1414
		f 3 3929 3930 -3929
		mu 0 3 1414 1416 1415
		f 3 -3931 3931 3932
		mu 0 3 1415 1416 1417
		f 3 -3933 3933 3934
		mu 0 3 1415 1417 1418
		f 3 -3935 3935 3936
		mu 0 3 1415 1418 1419
		f 3 -3936 3937 3938
		mu 0 3 1419 1418 1420
		f 3 3939 3940 -3939
		mu 0 3 1420 1421 1419
		f 3 3941 -3941 3942
		mu 0 3 1422 1419 1421
		f 3 3943 -3943 3944
		mu 0 3 1423 1422 1421
		f 3 -3945 3945 3946
		mu 0 3 1423 1421 1424
		f 3 -3947 3947 3948
		mu 0 3 1423 1424 1425
		f 3 3949 3950 -3948
		mu 0 3 1424 1426 1425
		f 3 3951 3952 -3951
		mu 0 3 1426 1427 1425
		f 3 3953 -3953 3954
		mu 0 3 1428 1425 1427
		f 3 3955 -3955 3956
		mu 0 3 1429 1428 1427
		f 3 3957 3958 -3957
		mu 0 3 1427 1430 1429
		f 3 3959 3960 -3959
		mu 0 3 1430 1431 1429;
	setAttr ".fc[2500:2999]"
		f 3 3961 -3961 3962
		mu 0 3 1432 1429 1431
		f 3 3963 3964 -3963
		mu 0 3 1431 1433 1432
		f 3 3965 3966 -3965
		mu 0 3 1433 1434 1432
		f 3 -3967 3967 3968
		mu 0 3 1432 1434 1435
		f 3 3969 3970 -3968
		mu 0 3 1434 1436 1435
		f 3 3971 -3971 3972
		mu 0 3 1437 1435 1436
		f 3 3973 -3973 3974
		mu 0 3 1438 1437 1436
		f 3 -3975 3975 3976
		mu 0 3 1438 1436 1439
		f 3 3977 -3976 3978
		mu 0 3 1440 1439 1436
		f 3 -3978 3979 3980
		mu 0 3 1439 1440 1441
		f 3 3981 -3981 3982
		mu 0 3 1442 1439 1441
		f 3 3983 3984 -3983
		mu 0 3 1441 1443 1442
		f 3 3985 3986 -3985
		mu 0 3 1443 1444 1442
		f 3 3987 3988 -3987
		mu 0 3 1444 1445 1442
		f 3 -3988 3989 3990
		mu 0 3 1445 1444 1446
		f 3 3991 -3990 3992
		mu 0 3 1447 1446 1444
		f 3 -3993 3993 3994
		mu 0 3 1447 1444 1448
		f 3 3995 -3995 3996
		mu 0 3 1449 1447 1448
		f 3 -3997 3997 3998
		mu 0 3 1449 1448 1450
		f 3 3999 4000 -3999
		mu 0 3 1450 1451 1449
		f 3 4001 4002 -4001
		mu 0 3 1451 1452 1449
		f 3 4003 4004 -4003
		mu 0 3 1452 1453 1449
		f 3 -4004 4005 4006
		mu 0 3 1453 1452 1454
		f 3 4007 -4006 4008
		mu 0 3 1455 1454 1452
		f 3 4009 -4009 4010
		mu 0 3 1456 1455 1452
		f 3 -4010 4011 4012
		mu 0 3 1455 1456 1457
		f 3 4013 4014 -4012
		mu 0 3 1456 1458 1457
		f 3 4015 -4015 4016
		mu 0 3 1459 1457 1458
		f 3 4017 4018 -4017
		mu 0 3 1458 1460 1459
		f 3 4019 4020 -4019
		mu 0 3 1460 1461 1459
		f 3 4021 -4021 4022
		mu 0 3 1462 1459 1461
		f 3 4023 -4023 4024
		mu 0 3 1463 1462 1461
		f 3 4025 4026 -4025
		mu 0 3 1461 1464 1463
		f 3 4027 -4027 4028
		mu 0 3 1465 1463 1464
		f 3 4029 4030 -4029
		mu 0 3 1464 1466 1465
		f 3 4031 -4031 4032
		mu 0 3 1467 1465 1466
		f 3 4033 4034 -4033
		mu 0 3 1466 1468 1467
		f 3 4035 -4035 4036
		mu 0 3 1469 1467 1468
		f 3 4037 4038 -4037
		mu 0 3 1468 1470 1469
		f 3 4039 -4039 4040
		mu 0 3 1471 1469 1470
		f 3 4041 4042 -4041
		mu 0 3 1470 1472 1471
		f 3 4043 -4043 4044
		mu 0 3 1473 1471 1472
		f 3 -4045 4045 4046
		mu 0 3 1473 1472 1474
		f 3 4047 -4047 4048
		mu 0 3 1475 1473 1474
		f 3 4049 -4049 4050
		mu 0 3 1476 1475 1474
		f 3 4051 4052 -4051
		mu 0 3 1474 1477 1476
		f 3 4053 -4053 4054
		mu 0 3 1478 1476 1477
		f 3 4055 -4055 4056
		mu 0 3 1479 1478 1477
		f 3 4057 4058 -4057
		mu 0 3 1477 1480 1479
		f 3 4059 4060 -4059
		mu 0 3 1480 1481 1479
		f 3 4061 -4061 4062
		mu 0 3 1482 1479 1481
		f 3 4063 4064 -4063
		mu 0 3 1481 1483 1482
		f 3 4065 -4065 4066
		mu 0 3 1484 1482 1483
		f 3 4067 4068 -4067
		mu 0 3 1483 1485 1484
		f 3 -4068 4069 4070
		mu 0 3 1485 1483 1486
		f 3 4071 -4070 4072
		mu 0 3 1487 1486 1483
		f 3 4073 -4072 4074
		mu 0 3 1488 1486 1487
		f 3 4075 -4075 4076
		mu 0 3 1489 1488 1487
		f 3 4077 -4077 4078
		mu 0 3 1490 1489 1487
		f 3 -4079 4079 4080
		mu 0 3 1490 1487 1481
		f 3 4081 -4078 4082
		mu 0 3 1491 1489 1490
		f 3 4083 4084 -4083
		mu 0 3 1490 1492 1491
		f 3 4085 4086 -4085
		mu 0 3 1492 1493 1491
		f 3 4087 -4087 4088
		mu 0 3 1494 1491 1493
		f 3 4089 -4089 4090
		mu 0 3 1495 1494 1493
		f 3 4091 -4091 4092
		mu 0 3 1496 1495 1493
		f 3 -4092 4093 4094
		mu 0 3 1495 1496 1470
		f 3 -4090 4095 4096
		mu 0 3 1494 1495 1497
		f 3 4097 4098 -4096
		mu 0 3 1495 1498 1497
		f 3 4099 4100 -4099
		mu 0 3 1498 1499 1497
		f 3 -4101 4101 4102
		mu 0 3 1497 1499 1500
		f 3 4103 -4102 4104
		mu 0 3 1501 1500 1499
		f 3 4105 4106 -4105
		mu 0 3 1499 1502 1501
		f 3 4107 4108 -4107
		mu 0 3 1502 1503 1501
		f 3 4109 4110 -4109
		mu 0 3 1503 1504 1501
		f 3 -4110 4111 4112
		mu 0 3 1504 1503 1505
		f 3 4113 -4113 4114
		mu 0 3 1506 1504 1505
		f 3 -4115 4115 4116
		mu 0 3 1506 1505 1507
		f 3 -4117 4117 4118
		mu 0 3 1506 1507 1508
		f 3 4119 4120 -4118
		mu 0 3 1507 1509 1508
		f 3 4121 -4121 4122
		mu 0 3 1510 1508 1509
		f 3 -4123 4123 4124
		mu 0 3 1510 1509 1511
		f 3 4125 -4125 4126
		mu 0 3 1512 1510 1511
		f 3 4127 4128 -4127
		mu 0 3 1511 1513 1512
		f 3 -4129 4129 4130
		mu 0 3 1512 1513 1514
		f 3 4131 -4130 4132
		mu 0 3 1515 1514 1513
		f 3 4133 4134 -4133
		mu 0 3 1513 1516 1515
		f 3 4135 -4135 4136
		mu 0 3 1517 1515 1516
		f 3 4137 -4137 4138
		mu 0 3 1518 1517 1516
		f 3 4139 -4139 4140
		mu 0 3 1519 1518 1516
		f 3 4141 -4140 4142
		mu 0 3 1520 1518 1519
		f 3 4143 4144 -4143
		mu 0 3 1519 1521 1520
		f 3 4145 4146 -4145
		mu 0 3 1521 1522 1520
		f 3 4147 4148 -4147
		mu 0 3 1522 1523 1520
		f 3 4149 4150 -4149
		mu 0 3 1523 1524 1520
		f 3 -4150 4151 4152
		mu 0 3 1524 1523 1525
		f 3 4153 4154 -4153
		mu 0 3 1525 1526 1524
		f 3 -4155 4155 4156
		mu 0 3 1524 1526 1527
		f 3 4157 -4156 4158
		mu 0 3 1528 1527 1526
		f 3 4159 4160 -4159
		mu 0 3 1526 1529 1528
		f 3 4161 -4161 4162
		mu 0 3 1530 1528 1529
		f 3 4163 4164 -4163
		mu 0 3 1529 1531 1530
		f 3 4165 -4165 4166
		mu 0 3 1532 1530 1531
		f 3 4167 4168 -4167
		mu 0 3 1531 1533 1532
		f 3 4169 4170 -4169
		mu 0 3 1533 1534 1532
		f 3 -4171 4171 4172
		mu 0 3 1532 1534 1535
		f 3 -4172 4173 4174
		mu 0 3 1535 1534 1536
		f 3 4175 4176 -4174
		mu 0 3 1534 1537 1536
		f 3 -4177 4177 4178
		mu 0 3 1536 1537 1538
		f 3 -4178 4179 4180
		mu 0 3 1538 1537 1539
		f 3 -4181 4181 4182
		mu 0 3 1538 1539 1540
		f 3 -4182 4183 4184
		mu 0 3 1540 1539 1541
		f 3 4185 4186 -4185
		mu 0 3 1541 1542 1540
		f 3 4187 -4187 4188
		mu 0 3 1543 1540 1542
		f 3 4189 4190 -4189
		mu 0 3 1542 1544 1543
		f 3 4191 -4191 4192
		mu 0 3 1545 1543 1544
		f 3 -4193 4193 4194
		mu 0 3 1545 1544 1546
		f 3 4195 -4194 4196
		mu 0 3 1547 1546 1544
		f 3 4197 4198 -4197
		mu 0 3 1544 1548 1547
		f 3 4199 -4199 4200
		mu 0 3 1549 1547 1548
		f 3 4201 4202 -4201
		mu 0 3 1548 1550 1549
		f 3 4203 -4203 4204
		mu 0 3 1551 1549 1550
		f 3 4205 4206 -4205
		mu 0 3 1550 1552 1551
		f 3 4207 -4207 4208
		mu 0 3 1553 1551 1552
		f 3 4209 4210 -4209
		mu 0 3 1552 1554 1553
		f 3 4211 -4211 4212
		mu 0 3 1555 1553 1554
		f 3 4213 4214 -4213
		mu 0 3 1554 1556 1555
		f 3 4215 -4215 4216
		mu 0 3 1557 1555 1556
		f 3 4217 4218 -4217
		mu 0 3 1556 1558 1557
		f 3 4219 -4219 4220
		mu 0 3 1559 1557 1558
		f 3 -4221 4221 4222
		mu 0 3 1559 1558 1560
		f 3 4223 4224 -4222
		mu 0 3 1558 1561 1560
		f 3 4225 -4225 4226
		mu 0 3 1562 1560 1561
		f 3 4227 4228 -4227
		mu 0 3 1561 1563 1562
		f 3 4229 4230 -4229
		mu 0 3 1563 1564 1562
		f 3 4231 -4231 4232
		mu 0 3 1565 1562 1564
		f 3 4233 4234 -4233
		mu 0 3 1564 1566 1565
		f 3 4235 -4235 4236
		mu 0 3 1567 1565 1566
		f 3 4237 4238 -4237
		mu 0 3 1566 1568 1567
		f 3 4239 -4239 4240
		mu 0 3 1569 1567 1568
		f 3 -4241 4241 4242
		mu 0 3 1569 1568 1570
		f 3 4243 -4242 4244
		mu 0 3 1571 1570 1568
		f 3 -4244 4245 4246
		mu 0 3 1570 1571 1572
		f 3 4247 4248 -4246
		mu 0 3 1571 1573 1572
		f 3 4249 4250 -4249
		mu 0 3 1573 1574 1572
		f 3 4251 -4251 4252
		mu 0 3 1575 1572 1574
		f 3 4253 4254 -4253
		mu 0 3 1574 1576 1575
		f 3 4255 4256 -4255
		mu 0 3 1576 1577 1575
		f 3 -4257 4257 4258
		mu 0 3 1575 1577 1578
		f 3 -4259 4259 4260
		mu 0 3 1575 1578 1570
		f 3 -4256 4261 4262
		mu 0 3 1577 1576 1579
		f 3 4263 -4262 4264
		mu 0 3 1580 1579 1576
		f 3 4265 -4265 4266
		mu 0 3 1581 1580 1576
		f 3 -4266 4267 4268
		mu 0 3 1580 1581 1582
		f 3 4269 4270 -4269
		mu 0 3 1582 1583 1580
		f 3 4271 -4271 4272
		mu 0 3 1584 1580 1583
		f 3 4273 4274 -4273
		mu 0 3 1583 1585 1584
		f 3 -4275 4275 4276
		mu 0 3 1584 1585 1586
		f 3 4277 4278 -4276
		mu 0 3 1585 1587 1586
		f 3 4279 4280 -4279
		mu 0 3 1587 1588 1586
		f 3 -4281 4281 4282
		mu 0 3 1586 1588 1589
		f 3 4283 4284 -4282
		mu 0 3 1588 1590 1589
		f 3 -4285 4285 4286
		mu 0 3 1589 1590 1591
		f 3 4287 4288 -4286
		mu 0 3 1590 1592 1591
		f 3 -4289 4289 4290
		mu 0 3 1591 1592 1593
		f 3 4291 4292 -4290
		mu 0 3 1592 1594 1593
		f 3 4293 -4293 4294
		mu 0 3 1595 1593 1594
		f 3 -4295 4295 4296
		mu 0 3 1595 1594 1596
		f 3 4297 -4296 4298
		mu 0 3 1597 1596 1594
		f 3 -4299 4299 4300
		mu 0 3 1597 1594 1598
		f 3 4301 -4301 4302
		mu 0 3 1599 1597 1598
		f 3 -4303 4303 4304
		mu 0 3 1599 1598 1600
		f 3 4305 4306 -4305
		mu 0 3 1600 1601 1599
		f 3 4307 4308 -4307
		mu 0 3 1601 1602 1599
		f 3 -4308 4309 4310
		mu 0 3 1602 1601 1603
		f 3 -4310 4311 4312
		mu 0 3 1603 1601 1604
		f 3 4313 -4313 4314
		mu 0 3 1605 1603 1604
		f 3 -4315 4315 4316
		mu 0 3 1605 1604 1606
		f 3 4317 4318 -4316
		mu 0 3 1604 1607 1606
		f 3 4319 -4319 4320
		mu 0 3 1608 1606 1607
		f 3 4321 4322 -4321
		mu 0 3 1607 1609 1608
		f 3 4323 -4323 4324
		mu 0 3 1610 1608 1609
		f 3 -4325 4325 4326
		mu 0 3 1610 1609 1611
		f 3 -4326 4327 4328
		mu 0 3 1611 1609 1612
		f 3 4329 -4328 4330
		mu 0 3 1613 1612 1609
		f 3 -4330 4331 4332
		mu 0 3 1612 1613 1614
		f 3 4333 -4332 4334
		mu 0 3 1615 1614 1613
		f 3 4335 4336 -4335
		mu 0 3 1613 1616 1615
		f 3 4337 -4337 4338
		mu 0 3 1617 1615 1616
		f 3 4339 -4339 4340
		mu 0 3 1604 1617 1616
		f 3 -4338 4341 4342
		mu 0 3 1615 1617 1618
		f 3 4343 4344 -4342
		mu 0 3 1617 1619 1618
		f 3 -4345 4345 4346
		mu 0 3 1618 1619 1588
		f 3 -4344 4347 4348
		mu 0 3 1619 1617 1600
		f 3 4349 4350 -4349
		mu 0 3 1600 1620 1619
		f 3 4351 -4351 4352
		mu 0 3 1590 1619 1620
		f 3 4353 4354 -4343
		mu 0 3 1618 1587 1615
		f 3 -4336 4355 4356
		mu 0 3 1616 1613 1607
		f 3 -4334 -4355 4357
		mu 0 3 1614 1615 1587
		f 3 4358 4359 -4333
		mu 0 3 1614 1621 1612
		f 3 4360 -4360 4361
		mu 0 3 1622 1612 1621
		f 3 -4362 4362 4363
		mu 0 3 1622 1621 1623
		f 3 -4363 4364 4365
		mu 0 3 1623 1621 1583
		f 3 4366 -4364 4367
		mu 0 3 1624 1622 1623
		f 3 4368 4369 -4368
		mu 0 3 1623 1625 1624
		f 3 4370 -4370 4371
		mu 0 3 1626 1624 1625
		f 3 4372 4373 -4372
		mu 0 3 1625 1627 1626
		f 3 4374 4375 -4374
		mu 0 3 1627 1628 1626
		f 3 4376 4377 -4376
		mu 0 3 1628 1629 1626
		f 3 -4377 4378 4379
		mu 0 3 1629 1628 1420
		f 3 4380 4381 -4380
		mu 0 3 1420 1630 1629
		f 3 4382 4383 -4382
		mu 0 3 1630 1631 1629
		f 3 -4384 4384 4385
		mu 0 3 1629 1631 1624
		f 3 4386 4387 -4383
		mu 0 3 1630 1632 1631
		f 3 4388 -4388 4389
		mu 0 3 1611 1631 1632
		f 3 -4389 4390 4391
		mu 0 3 1631 1611 1622
		f 3 4392 -4387 4393
		mu 0 3 1633 1632 1630
		f 3 4394 -4394 4395
		mu 0 3 1418 1633 1630
		f 3 4396 4397 -4393
		mu 0 3 1633 1634 1632
		f 3 4398 -4398 4399
		mu 0 3 1610 1632 1634
		f 3 4400 -4400 4401
		mu 0 3 1635 1610 1634
		f 3 4402 4403 -4402
		mu 0 3 1634 1636 1635
		f 3 4404 4405 -4404
		mu 0 3 1636 1637 1635
		f 3 4406 -4406 4407
		mu 0 3 1638 1635 1637
		f 3 4408 -4408 4409
		mu 0 3 1639 1638 1637
		f 3 4410 -4410 4411
		mu 0 3 1640 1639 1637
		f 3 4412 4413 -4412
		mu 0 3 1637 1641 1640
		f 3 -4413 4414 4415
		mu 0 3 1641 1637 1642
		f 3 4416 4417 -4416
		mu 0 3 1642 1643 1641
		f 3 -4417 4418 4419
		mu 0 3 1643 1642 1644
		f 3 4420 4421 -4419
		mu 0 3 1642 1645 1644
		f 3 4422 4423 -4422
		mu 0 3 1645 1646 1644
		f 3 4424 -4424 4425
		mu 0 3 1647 1644 1646
		f 3 4426 4427 -4426
		mu 0 3 1646 1648 1647
		f 3 -4427 4428 4429
		mu 0 3 1648 1646 1649
		f 3 4430 -4429 4431
		mu 0 3 1650 1649 1646
		f 3 -4431 4432 4433
		mu 0 3 1649 1650 1651
		f 3 4434 4435 -4434
		mu 0 3 1651 1652 1649
		f 3 4436 -4436 4437
		mu 0 3 1653 1649 1652
		f 3 4438 4439 -4438
		mu 0 3 1652 1654 1653
		f 3 -4439 4440 4441
		mu 0 3 1654 1652 1655
		f 3 4442 -4441 4443
		mu 0 3 1656 1655 1652
		f 3 -4443 4444 4445
		mu 0 3 1655 1656 1403
		f 3 4446 4447 -4442
		mu 0 3 1655 1657 1654
		f 3 -4447 4448 4449
		mu 0 3 1657 1655 1401
		f 3 -4435 4450 -4444
		mu 0 3 1652 1651 1656
		f 3 4451 -4451 4452
		mu 0 3 1658 1656 1651
		f 3 -4452 4453 4454
		mu 0 3 1656 1658 1405
		f 3 4455 4456 -4454
		mu 0 3 1658 1659 1405
		f 3 -4456 4457 4458
		mu 0 3 1659 1658 1416
		f 3 4459 -4458 4460
		mu 0 3 1660 1416 1658
		f 3 4461 4462 -4461
		mu 0 3 1658 1650 1660
		f 3 -4463 4463 4464
		mu 0 3 1660 1650 1645
		f 3 -4465 4465 4466
		mu 0 3 1660 1645 1661
		f 3 -4466 4467 4468
		mu 0 3 1661 1645 1636
		f 3 4469 4470 -4467
		mu 0 3 1661 1417 1660
		f 3 -4470 4471 4472
		mu 0 3 1417 1661 1633
		f 3 -4453 -4433 -4462
		mu 0 3 1658 1651 1650
		f 3 -4437 4473 -4430
		mu 0 3 1649 1653 1648
		f 3 -4423 -4464 -4432
		mu 0 3 1646 1645 1650
		f 3 -4421 4474 -4468
		mu 0 3 1645 1642 1636
		f 3 -4425 4475 -4420
		mu 0 3 1644 1647 1643
		f 3 4476 4477 -4409
		mu 0 3 1639 1662 1638
		f 3 4478 4479 -4478
		mu 0 3 1662 1606 1638
		f 3 -4407 4480 4481
		mu 0 3 1635 1638 1608
		f 3 -4405 -4475 -4415
		mu 0 3 1637 1636 1642
		f 3 -4403 4482 -4469
		mu 0 3 1636 1634 1661
		f 3 -4483 -4397 -4472
		mu 0 3 1661 1634 1633
		f 3 -4375 4483 4484
		mu 0 3 1628 1627 1424
		f 3 -4373 4485 4486
		mu 0 3 1627 1625 1663
		f 3 4487 -4486 4488
		mu 0 3 1582 1663 1625
		f 3 4489 4490 -4487
		mu 0 3 1663 1426 1627
		f 3 -4490 4491 4492
		mu 0 3 1426 1663 1664
		f 3 4493 -4492 4494
		mu 0 3 1581 1664 1663
		f 3 -4494 4495 4496
		mu 0 3 1664 1581 1574
		f 3 4497 4498 -4493
		mu 0 3 1664 1665 1426
		f 3 -4498 4499 4500
		mu 0 3 1665 1664 1573
		f 3 -4501 4501 4502
		mu 0 3 1665 1573 1666
		f 3 4503 4504 -4503
		mu 0 3 1666 1430 1665
		f 3 4505 4506 -4504
		mu 0 3 1666 1667 1430
		f 3 -4506 4507 4508
		mu 0 3 1667 1666 1668
		f 3 4509 -4508 4510
		mu 0 3 1571 1668 1666
		f 3 -4510 4511 4512
		mu 0 3 1668 1571 1566
		f 3 4513 4514 -4509
		mu 0 3 1668 1669 1667
		f 3 4515 4516 -4515
		mu 0 3 1669 1670 1667
		f 3 -4517 4517 4518
		mu 0 3 1667 1670 1431
		f 3 4519 -4516 4520
		mu 0 3 1563 1670 1669
		f 3 -4520 4521 4522
		mu 0 3 1670 1563 1671
		f 3 -4522 4523 4524
		mu 0 3 1671 1563 1672
		f 3 4525 4526 -4525
		mu 0 3 1672 1673 1671
		f 3 4527 4528 -4527
		mu 0 3 1673 1674 1671
		f 3 4529 -4529 4530
		mu 0 3 1675 1671 1674
		f 3 4531 -4531 4532
		mu 0 3 1676 1675 1674
		f 3 4533 4534 -4533
		mu 0 3 1674 1677 1676
		f 3 4535 4536 -4535
		mu 0 3 1677 1678 1676
		f 3 4537 -4537 4538
		mu 0 3 1679 1676 1678
		f 3 4539 4540 -4539
		mu 0 3 1678 1680 1679
		f 3 4541 4542 -4541
		mu 0 3 1680 1441 1679
		f 3 4543 4544 -4540
		mu 0 3 1678 1681 1680
		f 3 4545 4546 -4545
		mu 0 3 1681 1682 1680
		f 3 -4547 4547 4548
		mu 0 3 1680 1682 1443
		f 3 4549 4550 -4548
		mu 0 3 1682 1683 1443
		f 3 -4550 4551 4552
		mu 0 3 1683 1682 1684
		f 3 4553 4554 -4553
		mu 0 3 1684 1450 1683
		f 3 4555 -4554 4556
		mu 0 3 1685 1450 1684
		f 3 4557 4558 -4557
		mu 0 3 1684 1686 1685
		f 3 4559 -4559 4560
		mu 0 3 1687 1685 1686
		f 3 -4561 4561 4562
		mu 0 3 1687 1686 1688
		f 3 4563 4564 -4562
		mu 0 3 1686 1689 1688
		f 3 4565 -4565 4566
		mu 0 3 1690 1688 1689
		f 3 4567 4568 -4567
		mu 0 3 1689 1691 1690
		f 3 4569 4570 -4569
		mu 0 3 1691 1692 1690
		f 3 4571 4572 -4571
		mu 0 3 1692 1693 1690
		f 3 -4572 4573 4574
		mu 0 3 1693 1692 1694
		f 3 4575 4576 -4574
		mu 0 3 1692 1695 1694
		f 3 4577 -4577 4578
		mu 0 3 1696 1694 1695
		f 3 -4579 4579 4580
		mu 0 3 1696 1695 1525
		f 3 4581 -4580 4582
		mu 0 3 1697 1525 1695
		f 3 -4582 4583 4584
		mu 0 3 1525 1697 1698
		f 3 -4584 4585 4586
		mu 0 3 1698 1697 1699
		f 3 4587 4588 -4586
		mu 0 3 1697 1700 1699
		f 3 4589 4590 -4589
		mu 0 3 1700 1701 1699
		f 3 -4591 4591 4592
		mu 0 3 1699 1701 1531
		f 3 4593 4594 -4590
		mu 0 3 1700 1702 1701
		f 3 4595 -4595 4596
		mu 0 3 1703 1701 1702
		f 3 4597 -4597 4598
		mu 0 3 1704 1703 1702
		f 3 4599 -4599 4600
		mu 0 3 1705 1704 1702
		f 3 -4601 4601 4602
		mu 0 3 1705 1702 1691
		f 3 -4600 4603 4604
		mu 0 3 1704 1705 1706
		f 3 4605 4606 -4605
		mu 0 3 1706 1681 1704
		f 3 4607 4608 -4607
		mu 0 3 1681 1707 1704
		f 3 4609 4610 -4604
		mu 0 3 1705 1708 1706
		f 3 4611 -4611 4612
		mu 0 3 1684 1706 1708
		f 3 -4610 4613 4614
		mu 0 3 1708 1705 1689
		f 3 -4598 -4609 4615
		mu 0 3 1703 1704 1707
		f 3 4616 4617 -4616
		mu 0 3 1707 1709 1703
		f 3 4618 4619 -4618
		mu 0 3 1709 1533 1703
		f 3 -4619 4620 4621
		mu 0 3 1533 1709 1710
		f 3 4622 4623 -4621
		mu 0 3 1709 1711 1710
		f 3 4624 -4624 4625
		mu 0 3 1712 1710 1711
		f 3 4626 4627 -4626
		mu 0 3 1711 1713 1712
		f 3 4628 -4628 4629
		mu 0 3 1714 1712 1713
		f 3 4630 4631 -4630
		mu 0 3 1713 1715 1714
		f 3 4632 -4632 4633
		mu 0 3 1716 1714 1715
		f 3 4634 4635 -4634
		mu 0 3 1715 1717 1716
		f 3 4636 -4636 4637
		mu 0 3 1718 1716 1717
		f 3 4638 4639 -4638
		mu 0 3 1717 1550 1718
		f 3 -4637 4640 4641
		mu 0 3 1716 1718 1541
		f 3 4642 4643 -4642
		mu 0 3 1541 1719 1716
		f 3 -4635 4644 4645
		mu 0 3 1717 1715 1720
		f 3 4646 4647 -4646
		mu 0 3 1720 1552 1717
		f 3 4648 -4645 4649
		mu 0 3 1721 1720 1715
		f 3 -4649 4650 4651
		mu 0 3 1720 1721 1722
		f 3 4652 4653 -4652
		mu 0 3 1722 1554 1720
		f 3 4654 -4651 4655
		mu 0 3 1723 1722 1721
		f 3 4656 -4656 4657
		mu 0 3 1724 1723 1721
		f 3 -4658 4658 4659
		mu 0 3 1724 1721 1713
		f 3 4660 -4657 4661
		mu 0 3 1673 1723 1724
		f 3 4662 -4662 4663
		mu 0 3 1725 1673 1724
		f 3 4664 4665 -4664
		mu 0 3 1724 1711 1725
		f 3 -4655 4666 4667
		mu 0 3 1722 1723 1726
		f 3 4668 4669 -4668
		mu 0 3 1726 1556 1722
		f 3 4670 -4667 4671
		mu 0 3 1672 1726 1723
		f 3 -4671 4672 4673
		mu 0 3 1726 1672 1561
		f 3 -4633 -4644 4674
		mu 0 3 1714 1716 1719
		f 3 4675 -4675 4676
		mu 0 3 1537 1714 1719
		f 3 -4631 -4659 -4650
		mu 0 3 1715 1713 1721
		f 3 -4629 -4676 4677
		mu 0 3 1712 1714 1537
		f 3 -4665 -4660 -4627
		mu 0 3 1711 1724 1713
		f 3 -4625 4678 4679
		mu 0 3 1710 1712 1534
		f 3 -4623 4680 -4666
		mu 0 3 1711 1709 1725
		f 3 4681 -4681 4682
		mu 0 3 1677 1725 1709
		f 3 -4617 4683 -4683
		mu 0 3 1709 1707 1677
		f 3 -4596 -4620 4684
		mu 0 3 1701 1703 1533
		f 3 -4594 4685 -4602
		mu 0 3 1702 1700 1691
		f 3 -4588 4686 4687
		mu 0 3 1700 1697 1692
		f 3 -4587 4688 4689
		mu 0 3 1698 1699 1529
		f 3 4690 -4578 4691
		mu 0 3 1727 1694 1696
		f 3 4692 -4692 4693
		mu 0 3 1728 1727 1696
		f 3 4694 -4694 4695
		mu 0 3 1523 1728 1696
		f 3 -4693 4696 4697
		mu 0 3 1727 1728 1729
		f 3 4698 -4697 4699
		mu 0 3 1730 1729 1728
		f 3 4700 -4700 4701
		mu 0 3 1522 1730 1728
		f 3 -4701 4702 4703
		mu 0 3 1730 1522 1731
		f 3 4704 -4704 4705
		mu 0 3 1505 1730 1731
		f 3 4706 4707 -4705
		mu 0 3 1505 1732 1730
		f 3 -4699 -4708 4708
		mu 0 3 1729 1730 1732
		f 3 4709 -4709 4710
		mu 0 3 1733 1729 1732
		f 3 4711 4712 -4711
		mu 0 3 1732 1734 1733
		f 3 4713 4714 -4713
		mu 0 3 1734 1735 1733
		f 3 4715 -4715 4716
		mu 0 3 1736 1733 1735
		f 3 4717 -4717 4718
		mu 0 3 1737 1736 1735
		f 3 -4719 4719 4720
		mu 0 3 1737 1735 1738
		f 3 4721 4722 -4721
		mu 0 3 1738 1739 1737
		f 3 4723 4724 -4723
		mu 0 3 1739 1740 1737
		f 3 4725 -4725 4726
		mu 0 3 1687 1737 1740
		f 3 -4724 4727 4728
		mu 0 3 1740 1739 1451
		f 3 4729 4730 -4728
		mu 0 3 1739 1456 1451
		f 3 4731 -4729 4732
		mu 0 3 1685 1740 1451
		f 3 -4722 4733 4734
		mu 0 3 1739 1738 1458
		f 3 4735 -4720 4736
		mu 0 3 1741 1738 1735
		f 3 -4736 4737 4738
		mu 0 3 1738 1741 1460
		f 3 4739 -4738 4740
		mu 0 3 1742 1460 1741
		f 3 4741 4742 -4741
		mu 0 3 1741 1502 1742
		f 3 4743 -4743 4744
		mu 0 3 1743 1742 1502
		f 3 -4744 4745 4746
		mu 0 3 1742 1743 1464
		f 3 -4742 4747 4748
		mu 0 3 1502 1741 1734
		f 3 4749 -4718 -4726
		mu 0 3 1687 1736 1737
		f 3 -4750 4750 4751
		mu 0 3 1736 1687 1744
		f 3 4752 -4752 4753
		mu 0 3 1745 1736 1744
		f 3 4754 4755 -4754
		mu 0 3 1744 1693 1745
		f 3 4756 4757 -4755
		mu 0 3 1744 1688 1693
		f 3 -4753 4758 4759
		mu 0 3 1736 1745 1746
		f 3 -4759 4760 4761
		mu 0 3 1746 1745 1727
		f 3 -4716 -4760 4762
		mu 0 3 1733 1736 1746
		f 3 -4714 -4748 -4737
		mu 0 3 1735 1734 1741
		f 3 -4712 4763 4764
		mu 0 3 1734 1732 1503
		f 3 4765 -4710 -4763
		mu 0 3 1746 1729 1733
		f 3 -4762 -4698 -4766
		mu 0 3 1746 1727 1729
		f 3 4766 -4691 -4761
		mu 0 3 1745 1694 1727
		f 3 -4576 -4687 -4583
		mu 0 3 1695 1692 1697
		f 3 -4767 -4756 -4575
		mu 0 3 1694 1745 1693
		f 3 -4570 -4686 -4688
		mu 0 3 1692 1691 1700
		f 3 -4568 -4614 -4603
		mu 0 3 1691 1689 1705
		f 3 -4566 -4573 -4758
		mu 0 3 1688 1690 1693
		f 3 -4564 4767 -4615
		mu 0 3 1689 1686 1708
		f 3 -4757 -4751 -4563
		mu 0 3 1688 1744 1687
		f 3 -4560 -4727 -4732
		mu 0 3 1685 1687 1740
		f 3 -4558 -4613 -4768
		mu 0 3 1686 1684 1708
		f 3 -4612 -4552 4768
		mu 0 3 1706 1684 1682
		f 3 -4606 -4769 -4546
		mu 0 3 1681 1706 1682
		f 3 -4608 -4544 4769
		mu 0 3 1707 1681 1678
		f 3 -4538 4770 4771
		mu 0 3 1676 1679 1747
		f 3 4772 -4771 4773
		mu 0 3 1440 1747 1679
		f 3 -4773 4774 4775
		mu 0 3 1747 1440 1434
		f 3 -4536 -4684 -4770
		mu 0 3 1678 1677 1707
		f 3 -4534 4776 -4682
		mu 0 3 1677 1674 1725
		f 3 4777 -4532 -4772
		mu 0 3 1747 1675 1676
		f 3 -4778 4778 4779
		mu 0 3 1675 1747 1433
		f 3 4780 -4780 4781
		mu 0 3 1670 1675 1433
		f 3 -4528 -4663 -4777
		mu 0 3 1674 1673 1725
		f 3 -4526 -4672 -4661
		mu 0 3 1673 1672 1723
		f 3 -4530 -4781 -4523
		mu 0 3 1671 1675 1670
		f 3 -4514 4782 4783
		mu 0 3 1669 1668 1564
		f 3 -4386 -4371 -4378
		mu 0 3 1629 1624 1626
		f 3 -4369 4784 -4489
		mu 0 3 1625 1623 1582
		f 3 -4367 -4385 -4392
		mu 0 3 1622 1624 1631
		f 3 -4359 4785 4786
		mu 0 3 1621 1614 1585
		f 3 -4329 -4361 -4391
		mu 0 3 1611 1612 1622
		f 3 -4399 -4327 -4390
		mu 0 3 1632 1610 1611
		f 3 -4324 -4401 -4482
		mu 0 3 1608 1610 1635
		f 3 -4322 -4356 -4331
		mu 0 3 1609 1607 1613
		f 3 -4320 -4481 -4480
		mu 0 3 1606 1608 1638
		f 3 -4318 -4341 -4357
		mu 0 3 1607 1604 1616
		f 3 4787 -4317 -4479
		mu 0 3 1662 1605 1606
		f 3 -4312 4788 -4340
		mu 0 3 1604 1601 1617
		f 3 -4306 -4348 -4789
		mu 0 3 1601 1600 1617
		f 3 -4304 4789 -4350
		mu 0 3 1600 1598 1620
		f 3 4790 4791 -4790
		mu 0 3 1598 1592 1620
		f 3 4792 -4302 -4309
		mu 0 3 1602 1597 1599
		f 3 -4793 4793 4794
		mu 0 3 1597 1602 1748
		f 3 4795 -4298 -4795
		mu 0 3 1748 1596 1597
		f 3 4796 4797 -4796
		mu 0 3 1748 1749 1596
		f 3 4798 -4297 -4798
		mu 0 3 1749 1595 1596
		f 3 -4791 -4300 -4292
		mu 0 3 1592 1598 1594
		f 3 -4353 -4792 -4288
		mu 0 3 1590 1620 1592
		f 3 -4346 -4352 -4284
		mu 0 3 1588 1619 1590
		f 3 -4354 -4347 -4280
		mu 0 3 1587 1618 1588
		f 3 -4358 -4278 -4786
		mu 0 3 1614 1587 1585
		f 3 -4274 -4365 -4787
		mu 0 3 1585 1583 1621
		f 3 -4272 4799 4800
		mu 0 3 1580 1584 1750
		f 3 -4366 -4270 -4785
		mu 0 3 1623 1583 1582
		f 3 -4488 -4268 -4495
		mu 0 3 1663 1582 1581
		f 3 -4264 -4801 4801
		mu 0 3 1579 1580 1750
		f 3 -4254 -4496 -4267
		mu 0 3 1576 1574 1581
		f 3 -4250 -4500 -4497
		mu 0 3 1574 1573 1664
		f 3 -4248 -4511 -4502
		mu 0 3 1573 1571 1666
		f 3 -4252 -4261 -4247
		mu 0 3 1572 1575 1570
		f 3 -4260 4802 -4243
		mu 0 3 1570 1578 1569
		f 3 -4240 4803 4804
		mu 0 3 1567 1569 1751
		f 3 4805 4806 -4805
		mu 0 3 1751 1752 1567
		f 3 -4806 4807 4808
		mu 0 3 1752 1751 1753
		f 3 4809 4810 -4809
		mu 0 3 1753 1754 1752
		f 3 4811 -4811 4812
		mu 0 3 1755 1752 1754
		f 3 -4813 4813 4814
		mu 0 3 1755 1754 1756
		f 3 -4815 4815 4816
		mu 0 3 1755 1756 1560
		f 3 -4812 4817 4818
		mu 0 3 1752 1755 1565
		f 3 -4810 4819 4820
		mu 0 3 1754 1753 1757
		f 3 4821 -4820 4822
		mu 0 3 1758 1757 1753
		f 3 4823 4824 -4823
		mu 0 3 1753 1759 1758
		f 3 4825 4826 -4825
		mu 0 3 1759 1760 1758
		f 3 -4826 4827 4828
		mu 0 3 1760 1759 1761
		f 3 -4828 4829 4830
		mu 0 3 1761 1759 1762
		f 3 4831 4832 -4831
		mu 0 3 1762 1763 1761
		f 3 -4824 4833 -4830
		mu 0 3 1759 1753 1762
		f 3 4834 -4834 -4808
		mu 0 3 1751 1762 1753
		f 3 -4238 -4512 -4245
		mu 0 3 1568 1566 1571
		f 3 -4819 -4236 -4807
		mu 0 3 1752 1565 1567
		f 3 -4234 -4783 -4513
		mu 0 3 1566 1564 1668
		f 3 -4232 -4818 4835
		mu 0 3 1562 1565 1755;
	setAttr ".fc[3000:3380]"
		f 3 -4230 -4521 -4784
		mu 0 3 1564 1563 1669
		f 3 -4228 -4673 -4524
		mu 0 3 1563 1561 1672
		f 3 -4836 -4817 -4226
		mu 0 3 1562 1755 1560
		f 3 -4224 4836 -4674
		mu 0 3 1561 1558 1726
		f 3 4837 -4223 -4816
		mu 0 3 1756 1559 1560
		f 3 -4669 -4837 -4218
		mu 0 3 1556 1726 1558
		f 3 -4653 -4670 -4214
		mu 0 3 1554 1722 1556
		f 3 -4647 -4654 -4210
		mu 0 3 1552 1720 1554
		f 3 -4639 -4648 -4206
		mu 0 3 1550 1717 1552
		f 3 4838 -4640 -4202
		mu 0 3 1548 1718 1550
		f 3 -4839 4839 4840
		mu 0 3 1718 1548 1542
		f 3 4841 4842 -4195
		mu 0 3 1546 1764 1545
		f 3 4843 -4843 4844
		mu 0 3 1765 1545 1764
		f 3 4845 -4845 4846
		mu 0 3 1766 1765 1764
		f 3 4847 -4846 4848
		mu 0 3 1767 1765 1766
		f 3 4849 4850 -4849
		mu 0 3 1766 1768 1767
		f 3 4851 -4851 4852
		mu 0 3 1515 1767 1768
		f 3 4853 4854 -4848
		mu 0 3 1767 1769 1765
		f 3 -4855 4855 4856
		mu 0 3 1765 1769 1770
		f 3 4857 4858 -4856
		mu 0 3 1769 1771 1770
		f 3 4859 -4859 4860
		mu 0 3 1772 1770 1771
		f 3 4861 4862 -4861
		mu 0 3 1771 1773 1772
		f 3 4863 -4863 4864
		mu 0 3 1538 1772 1773
		f 3 -4862 4865 4866
		mu 0 3 1773 1771 1774
		f 3 4867 4868 -4867
		mu 0 3 1774 1535 1773
		f 3 4869 -4868 4870
		mu 0 3 1530 1535 1774
		f 3 4871 -4866 4872
		mu 0 3 1775 1774 1771
		f 3 4873 -4872 4874
		mu 0 3 1528 1774 1775
		f 3 -4860 4875 4876
		mu 0 3 1770 1772 1543
		f 3 -4858 4877 -4873
		mu 0 3 1771 1769 1775
		f 3 4878 -4878 4879
		mu 0 3 1517 1775 1769
		f 3 4880 -4879 4881
		mu 0 3 1527 1775 1517
		f 3 -4854 4882 -4880
		mu 0 3 1769 1767 1517
		f 3 -4857 4883 -4844
		mu 0 3 1765 1770 1545
		f 3 -4884 -4877 -4192
		mu 0 3 1545 1770 1543
		f 3 -4190 -4840 -4198
		mu 0 3 1544 1542 1548
		f 3 -4876 4884 -4188
		mu 0 3 1543 1772 1540
		f 3 -4186 -4641 -4841
		mu 0 3 1542 1541 1718
		f 3 -4184 4885 -4643
		mu 0 3 1541 1539 1719
		f 3 -4864 -4183 -4885
		mu 0 3 1772 1538 1540
		f 3 -4677 -4886 -4180
		mu 0 3 1537 1719 1539
		f 3 4886 -4179 -4865
		mu 0 3 1773 1536 1538
		f 3 -4679 -4678 -4176
		mu 0 3 1534 1712 1537
		f 3 -4887 -4869 -4175
		mu 0 3 1536 1773 1535
		f 3 -4170 -4622 -4680
		mu 0 3 1534 1533 1710
		f 3 -4168 -4592 -4685
		mu 0 3 1533 1531 1701
		f 3 -4166 -4173 -4870
		mu 0 3 1530 1532 1535
		f 3 -4164 -4689 -4593
		mu 0 3 1531 1529 1699
		f 3 -4162 -4871 -4874
		mu 0 3 1528 1530 1774
		f 3 -4160 4887 -4690
		mu 0 3 1529 1526 1698
		f 3 -4158 -4875 -4881
		mu 0 3 1527 1528 1775
		f 3 4888 -4157 4889
		mu 0 3 1518 1524 1527
		f 3 -4154 -4585 -4888
		mu 0 3 1526 1525 1698
		f 3 -4696 -4581 -4152
		mu 0 3 1523 1696 1525
		f 3 -4695 -4148 -4702
		mu 0 3 1728 1523 1522
		f 3 4890 -4703 -4146
		mu 0 3 1521 1731 1522
		f 3 -4891 4891 4892
		mu 0 3 1731 1521 1509
		f 3 -4144 4893 4894
		mu 0 3 1521 1519 1511
		f 3 -4142 -4151 -4889
		mu 0 3 1518 1520 1524
		f 3 -4138 -4890 -4882
		mu 0 3 1517 1518 1527
		f 3 -4136 -4883 -4852
		mu 0 3 1515 1517 1767
		f 3 4895 -4141 -4134
		mu 0 3 1513 1519 1516
		f 3 4896 -4132 -4853
		mu 0 3 1768 1514 1515
		f 3 -4897 4897 4898
		mu 0 3 1514 1768 1776
		f 3 4899 4900 -4899
		mu 0 3 1776 1777 1514
		f 3 -4900 4901 4902
		mu 0 3 1777 1776 1778
		f 3 4903 4904 -4903
		mu 0 3 1778 1779 1777
		f 3 4905 -4905 4906
		mu 0 3 1780 1777 1779
		f 3 4907 4908 -4907
		mu 0 3 1779 1781 1780
		f 3 4909 4910 -4909
		mu 0 3 1781 1782 1780
		f 3 4911 4912 -4911
		mu 0 3 1782 1510 1780
		f 3 4913 4914 -4910
		mu 0 3 1781 1783 1782
		f 3 4915 -4915 4916
		mu 0 3 1784 1782 1783
		f 3 4917 -4917 4918
		mu 0 3 1785 1784 1783
		f 3 4919 -4919 4920
		mu 0 3 1489 1785 1783
		f 3 4921 -4918 4922
		mu 0 3 1786 1784 1785
		f 3 4923 4924 -4923
		mu 0 3 1785 1494 1786
		f 3 4925 4926 -4925
		mu 0 3 1494 1500 1786
		f 3 4927 -4927 4928
		mu 0 3 1504 1786 1500
		f 3 -4922 4929 4930
		mu 0 3 1784 1786 1506
		f 3 -4916 4931 4932
		mu 0 3 1782 1784 1508
		f 3 -4914 4933 4934
		mu 0 3 1783 1781 1488
		f 3 4935 4936 -4934
		mu 0 3 1781 1787 1488
		f 3 -4908 4937 -4936
		mu 0 3 1781 1779 1787
		f 3 4938 -4938 4939
		mu 0 3 1788 1787 1779
		f 3 -4939 4940 4941
		mu 0 3 1787 1788 1789
		f 3 4942 4943 -4942
		mu 0 3 1789 1486 1787
		f 3 -4906 4944 4945
		mu 0 3 1777 1780 1512
		f 3 -4904 4946 -4940
		mu 0 3 1779 1778 1788
		f 3 -4946 -4131 -4901
		mu 0 3 1777 1512 1514
		f 3 -4128 -4894 -4896
		mu 0 3 1513 1511 1519
		f 3 -4126 -4945 -4913
		mu 0 3 1510 1512 1780
		f 3 -4892 -4895 -4124
		mu 0 3 1509 1521 1511
		f 3 -4122 -4912 -4933
		mu 0 3 1508 1510 1782
		f 3 -4120 4947 -4893
		mu 0 3 1509 1507 1731
		f 3 -4931 -4119 -4932
		mu 0 3 1784 1506 1508
		f 3 -4116 -4706 -4948
		mu 0 3 1507 1505 1731
		f 3 -4928 -4114 -4930
		mu 0 3 1786 1504 1506
		f 3 -4112 -4764 -4707
		mu 0 3 1505 1503 1732
		f 3 -4749 -4765 -4108
		mu 0 3 1502 1734 1503
		f 3 -4106 4948 -4745
		mu 0 3 1502 1499 1743
		f 3 -4104 -4111 -4929
		mu 0 3 1500 1501 1504
		f 3 4949 -4949 -4100
		mu 0 3 1498 1743 1499
		f 3 4950 -4950 4951
		mu 0 3 1466 1743 1498
		f 3 -4098 4952 4953
		mu 0 3 1498 1495 1468
		f 3 -4926 -4097 -4103
		mu 0 3 1500 1494 1497
		f 3 -4924 4954 -4088
		mu 0 3 1494 1785 1491
		f 3 4955 -4093 -4086
		mu 0 3 1492 1496 1493
		f 3 -4956 4956 4957
		mu 0 3 1496 1492 1790
		f 3 4958 4959 -4958
		mu 0 3 1790 1472 1496
		f 3 4960 4961 -4957
		mu 0 3 1492 1480 1790
		f 3 -4084 4962 -4961
		mu 0 3 1492 1490 1480
		f 3 -4082 -4955 -4920
		mu 0 3 1489 1491 1785
		f 3 -4076 -4921 -4935
		mu 0 3 1488 1489 1783
		f 3 -4937 -4944 -4074
		mu 0 3 1488 1787 1486
		f 3 -4943 4963 -4071
		mu 0 3 1486 1789 1485
		f 3 -4066 4964 4965
		mu 0 3 1482 1484 1791
		f 3 4966 4967 -4966
		mu 0 3 1791 1792 1482
		f 3 -4967 4968 4969
		mu 0 3 1792 1791 1793
		f 3 4970 4971 -4970
		mu 0 3 1793 1794 1792
		f 3 4972 -4972 4973
		mu 0 3 1478 1792 1794
		f 3 4974 -4974 4975
		mu 0 3 1795 1478 1794
		f 3 4976 4977 -4976
		mu 0 3 1794 1796 1795
		f 3 4978 4979 -4978
		mu 0 3 1796 1797 1795
		f 3 4980 4981 -4980
		mu 0 3 1797 1476 1795
		f 3 -4981 4982 4983
		mu 0 3 1476 1797 1798
		f 3 4984 -4983 4985
		mu 0 3 1799 1798 1797
		f 3 -4986 4986 4987
		mu 0 3 1799 1797 1800
		f 3 -4988 4988 4989
		mu 0 3 1799 1800 1801
		f 3 4990 -4989 4991
		mu 0 3 1802 1801 1800
		f 3 4992 4993 -4992
		mu 0 3 1800 1803 1802
		f 3 -4993 4994 4995
		mu 0 3 1803 1800 1796
		f 3 4996 4997 -4996
		mu 0 3 1796 1804 1803
		f 3 4998 4999 -4990
		mu 0 3 1801 1805 1799
		f 3 5000 5001 -5000
		mu 0 3 1805 1806 1799
		f 3 5002 5003 -5001
		mu 0 3 1805 1807 1806
		f 3 5004 5005 -5004
		mu 0 3 1807 1808 1806
		f 3 5006 5007 -5006
		mu 0 3 1808 1475 1806
		f 3 -5008 5008 5009
		mu 0 3 1806 1475 1798
		f 3 5010 5011 -5005
		mu 0 3 1807 1809 1808
		f 3 5012 5013 -5012
		mu 0 3 1809 1810 1808
		f 3 5014 5015 -5014
		mu 0 3 1810 1473 1808
		f 3 -5015 5016 5017
		mu 0 3 1473 1810 1811
		f 3 5018 5019 -5017
		mu 0 3 1810 1812 1811
		f 3 5020 -5020 5021
		mu 0 3 1813 1811 1812
		f 3 5022 5023 -5022
		mu 0 3 1812 1814 1813
		f 3 5024 -5024 5025
		mu 0 3 1815 1813 1814
		f 3 5026 5027 -5026
		mu 0 3 1814 1816 1815
		f 3 5028 -5028 5029
		mu 0 3 1817 1815 1816
		f 3 -5030 5030 5031
		mu 0 3 1817 1816 1818
		f 3 5032 -5032 5033
		mu 0 3 1819 1817 1818
		f 3 5034 5035 -5034
		mu 0 3 1818 1820 1819
		f 3 5036 -5036 5037
		mu 0 3 1821 1819 1820
		f 3 -5038 5038 5039
		mu 0 3 1821 1820 1822
		f 3 -5039 5040 5041
		mu 0 3 1822 1820 1823
		f 3 -5042 5042 5043
		mu 0 3 1822 1823 1824
		f 3 -5043 5044 5045
		mu 0 3 1824 1823 1337
		f 3 5046 -5044 5047
		mu 0 3 1825 1822 1824
		f 3 5048 5049 -5048
		mu 0 3 1824 1342 1825
		f 3 5050 5051 -5050
		mu 0 3 1342 1826 1825
		f 3 5052 -5052 5053
		mu 0 3 1827 1825 1826
		f 3 5054 -5054 5055
		mu 0 3 1828 1827 1826
		f 3 5056 -5056 5057
		mu 0 3 1343 1828 1826
		f 3 5058 5059 -5057
		mu 0 3 1343 1829 1828
		f 3 5060 5061 -5060
		mu 0 3 1829 1454 1828
		f 3 -5061 5062 5063
		mu 0 3 1454 1829 1830
		f 3 5064 -5063 5065
		mu 0 3 1358 1830 1829
		f 3 -5065 5066 5067
		mu 0 3 1830 1358 1831
		f 3 -5068 5068 5069
		mu 0 3 1830 1831 1453
		f 3 5070 5071 -5069
		mu 0 3 1831 1447 1453
		f 3 5072 5073 -5071
		mu 0 3 1831 1362 1447
		f 3 -5055 5074 5075
		mu 0 3 1827 1828 1455
		f 3 5076 5077 -5053
		mu 0 3 1827 1832 1825
		f 3 -5077 5078 5079
		mu 0 3 1832 1827 1833
		f 3 5080 -5080 5081
		mu 0 3 1462 1832 1833
		f 3 5082 -5081 5083
		mu 0 3 1821 1832 1462
		f 3 5084 -5079 5085
		mu 0 3 1457 1833 1827
		f 3 -5047 -5078 5086
		mu 0 3 1822 1825 1832
		f 3 5087 -5041 5088
		mu 0 3 1834 1823 1820
		f 3 -5088 5089 5090
		mu 0 3 1823 1834 1335
		f 3 -5083 -5040 -5087
		mu 0 3 1832 1821 1822
		f 3 -5037 5091 5092
		mu 0 3 1819 1821 1463
		f 3 -5035 5093 -5089
		mu 0 3 1820 1818 1834
		f 3 5094 5095 -5094
		mu 0 3 1818 1835 1834
		f 3 -5096 5096 5097
		mu 0 3 1834 1835 1334
		f 3 5098 -5097 5099
		mu 0 3 1836 1334 1835
		f 3 5100 5101 -5100
		mu 0 3 1835 1837 1836
		f 3 5102 5103 -5102
		mu 0 3 1837 1838 1836
		f 3 -5104 5104 5105
		mu 0 3 1836 1838 1331
		f 3 5106 -5105 5107
		mu 0 3 1839 1331 1838
		f 3 -5108 5108 5109
		mu 0 3 1839 1838 1840
		f 3 5110 5111 -5110
		mu 0 3 1840 1841 1839
		f 3 5112 5113 -5111
		mu 0 3 1840 1842 1841
		f 3 -5113 5114 5115
		mu 0 3 1842 1840 1843
		f 3 5116 -5115 5117
		mu 0 3 1844 1843 1840
		f 3 -5117 5118 5119
		mu 0 3 1843 1844 1812
		f 3 -5116 5120 5121
		mu 0 3 1842 1843 1810
		f 3 5122 -5118 -5109
		mu 0 3 1838 1844 1840
		f 3 -5103 5123 -5123
		mu 0 3 1838 1837 1844
		f 3 5124 -5124 5125
		mu 0 3 1814 1844 1837
		f 3 -5101 5126 5127
		mu 0 3 1837 1835 1816
		f 3 -5033 5128 5129
		mu 0 3 1817 1819 1465
		f 3 -5031 -5127 -5095
		mu 0 3 1818 1816 1835
		f 3 -5029 5130 5131
		mu 0 3 1815 1817 1467
		f 3 -5027 -5126 -5128
		mu 0 3 1816 1814 1837
		f 3 -5025 5132 5133
		mu 0 3 1813 1815 1469
		f 3 -5119 -5125 -5023
		mu 0 3 1812 1844 1814
		f 3 -5021 5134 5135
		mu 0 3 1811 1813 1471
		f 3 -5121 -5120 -5019
		mu 0 3 1810 1843 1812
		f 3 5136 -5122 -5013
		mu 0 3 1809 1842 1810
		f 3 -5002 -5010 -4985
		mu 0 3 1799 1806 1798
		f 3 -4995 -4987 -4979
		mu 0 3 1796 1800 1797
		f 3 -4997 -4977 5137
		mu 0 3 1804 1796 1794
		f 3 -4971 5138 -5138
		mu 0 3 1794 1793 1804
		f 3 -4064 -4080 -4073
		mu 0 3 1483 1481 1487
		f 3 -4062 -4968 5139
		mu 0 3 1479 1482 1792
		f 3 -4060 -4963 -4081
		mu 0 3 1481 1480 1490
		f 3 -4962 -4058 5140
		mu 0 3 1790 1480 1477
		f 3 -4973 -4056 -5140
		mu 0 3 1792 1478 1479
		f 3 -4054 -4975 -4982
		mu 0 3 1476 1478 1795
		f 3 -4052 5141 -5141
		mu 0 3 1477 1474 1790
		f 3 -4050 -4984 -5009
		mu 0 3 1475 1476 1798
		f 3 -5007 -5016 -4048
		mu 0 3 1475 1808 1473
		f 3 -4959 -5142 -4046
		mu 0 3 1472 1790 1474
		f 3 -4044 -5018 -5136
		mu 0 3 1471 1473 1811
		f 3 -4042 -4094 -4960
		mu 0 3 1472 1470 1496
		f 3 -5134 -4040 -5135
		mu 0 3 1813 1469 1471
		f 3 -4038 -4953 -4095
		mu 0 3 1470 1468 1495
		f 3 -4036 -5133 -5132
		mu 0 3 1467 1469 1815
		f 3 -4034 -4952 -4954
		mu 0 3 1468 1466 1498
		f 3 -4032 -5131 -5130
		mu 0 3 1465 1467 1817
		f 3 -4030 -4746 -4951
		mu 0 3 1466 1464 1743
		f 3 -4028 -5129 -5093
		mu 0 3 1463 1465 1819
		f 3 -4026 5142 -4747
		mu 0 3 1464 1461 1742
		f 3 -4024 -5092 -5084
		mu 0 3 1462 1463 1821
		f 3 -4022 -5082 5143
		mu 0 3 1459 1462 1833
		f 3 -4740 -5143 -4020
		mu 0 3 1460 1742 1461
		f 3 -4018 -4734 -4739
		mu 0 3 1460 1458 1738
		f 3 -4016 -5144 -5085
		mu 0 3 1457 1459 1833
		f 3 -4014 -4730 -4735
		mu 0 3 1458 1456 1739
		f 3 -5076 -4013 -5086
		mu 0 3 1827 1455 1457
		f 3 -4008 -5075 -5062
		mu 0 3 1454 1455 1828
		f 3 -5070 -4007 -5064
		mu 0 3 1830 1453 1454
		f 3 -4002 -4731 -4011
		mu 0 3 1452 1451 1456
		f 3 -4733 -4000 -4556
		mu 0 3 1685 1451 1450
		f 3 5144 -4555 -3998
		mu 0 3 1448 1683 1450
		f 3 -3996 -4005 -5072
		mu 0 3 1447 1449 1453
		f 3 -5145 -3994 5145
		mu 0 3 1683 1448 1444
		f 3 5146 -3992 -5074
		mu 0 3 1362 1446 1447
		f 3 5147 5148 -5147
		mu 0 3 1362 1845 1446
		f 3 5149 -5149 5150
		mu 0 3 1846 1446 1845
		f 3 5151 5152 -5151
		mu 0 3 1845 1847 1846
		f 3 5153 -5153 5154
		mu 0 3 1411 1846 1847
		f 3 -5154 5155 5156
		mu 0 3 1846 1411 1848
		f 3 5157 5158 -5157
		mu 0 3 1848 1445 1846
		f 3 -5158 5159 5160
		mu 0 3 1445 1848 1438
		f 3 5161 -5160 5162
		mu 0 3 1849 1438 1848
		f 3 -5156 5163 -5163
		mu 0 3 1848 1411 1849
		f 3 -5152 5164 5165
		mu 0 3 1847 1845 1363
		f 3 -5150 -5159 -3991
		mu 0 3 1446 1846 1445
		f 3 -3986 -4551 -5146
		mu 0 3 1444 1443 1683
		f 3 -3984 -4542 -4549
		mu 0 3 1443 1441 1680
		f 3 5166 -3982 -3989
		mu 0 3 1445 1439 1442
		f 3 -4543 -3980 -4774
		mu 0 3 1679 1441 1440
		f 3 -5167 -5161 -3977
		mu 0 3 1439 1445 1438
		f 3 -5162 5167 -3974
		mu 0 3 1438 1849 1437
		f 3 5168 5169 -5168
		mu 0 3 1849 1850 1437
		f 3 -5169 5170 5171
		mu 0 3 1850 1849 1851
		f 3 5172 5173 -5172
		mu 0 3 1851 1852 1850
		f 3 5174 5175 -5174
		mu 0 3 1852 1435 1850
		f 3 -5175 5176 5177
		mu 0 3 1435 1852 1428
		f 3 -5173 5178 5179
		mu 0 3 1852 1851 1423
		f 3 5180 -5171 5181
		mu 0 3 1412 1851 1849
		f 3 -5181 5182 5183
		mu 0 3 1851 1412 1422
		f 3 -5170 -5176 -3972
		mu 0 3 1437 1850 1435
		f 3 -3970 -4775 -3979
		mu 0 3 1436 1434 1440
		f 3 -5178 5184 -3969
		mu 0 3 1435 1428 1432
		f 3 -3966 -4779 -4776
		mu 0 3 1434 1433 1747
		f 3 -3964 -4518 -4782
		mu 0 3 1433 1431 1670
		f 3 -4519 -3960 -4507
		mu 0 3 1667 1431 1430
		f 3 -3958 5185 -4505
		mu 0 3 1430 1427 1665
		f 3 -3956 -3962 -5185
		mu 0 3 1428 1429 1432
		f 3 -3954 -5177 5186
		mu 0 3 1425 1428 1852
		f 3 -3952 -4499 -5186
		mu 0 3 1427 1426 1665
		f 3 -3950 -4484 -4491
		mu 0 3 1426 1424 1627
		f 3 -3949 -5187 -5180
		mu 0 3 1423 1425 1852
		f 3 5187 -4485 -3946
		mu 0 3 1421 1628 1424
		f 3 -3944 -5179 -5184
		mu 0 3 1422 1423 1851
		f 3 -3942 5188 5189
		mu 0 3 1419 1422 1413
		f 3 -3940 -4379 -5188
		mu 0 3 1421 1420 1628
		f 3 -4381 -3938 -4396
		mu 0 3 1630 1420 1418
		f 3 -4395 -3934 -4473
		mu 0 3 1633 1418 1417
		f 3 -4460 -4471 -3932
		mu 0 3 1416 1660 1417
		f 3 5190 -4459 -3930
		mu 0 3 1414 1659 1416
		f 3 5191 -5191 5192
		mu 0 3 1408 1659 1414
		f 3 -3928 -3937 -5190
		mu 0 3 1413 1415 1419
		f 3 -3925 -5189 -5183
		mu 0 3 1412 1413 1422
		f 3 -3923 -5182 -5164
		mu 0 3 1411 1412 1849
		f 3 5193 -3920 -5155
		mu 0 3 1847 1409 1411
		f 3 5194 5195 -5194
		mu 0 3 1847 1365 1409
		f 3 -3926 -3918 -5193
		mu 0 3 1414 1410 1408
		f 3 -3914 5196 -5192
		mu 0 3 1408 1406 1659
		f 3 -3910 5197 5198
		mu 0 3 1404 1407 1371
		f 3 -3908 -4457 -5197
		mu 0 3 1406 1405 1659
		f 3 -3906 -4445 -4455
		mu 0 3 1405 1403 1656
		f 3 -3904 -5199 5199
		mu 0 3 1402 1404 1371
		f 3 -3902 -4449 -4446
		mu 0 3 1403 1401 1655
		f 3 -3900 5200 5201
		mu 0 3 1399 1402 1372
		f 3 -3898 5202 -4450
		mu 0 3 1401 1400 1657
		f 3 -3818 -3880 -3827
		mu 0 3 1375 1373 1379
		f 3 -3816 -3895 -5202
		mu 0 3 1372 1374 1399
		f 3 -3814 5203 -3881
		mu 0 3 1373 1370 1397
		f 3 -3812 -5201 -5200
		mu 0 3 1371 1372 1402
		f 3 -3810 -5198 5204
		mu 0 3 1368 1371 1407
		f 3 -3808 -3875 -5204
		mu 0 3 1370 1369 1397
		f 3 -3806 5205 -3870
		mu 0 3 1369 1366 1396
		f 3 -3804 -5205 -3912
		mu 0 3 1367 1368 1407
		f 3 -3802 -3917 -5196
		mu 0 3 1365 1367 1409
		f 3 -3800 -3871 -5206
		mu 0 3 1366 1364 1396
		f 3 -3799 -5195 -5166
		mu 0 3 1363 1365 1847
		f 3 5206 -3872 -3796
		mu 0 3 1361 1395 1364
		f 3 -3794 -5165 -5148
		mu 0 3 1362 1363 1845
		f 3 -3792 -5073 5207
		mu 0 3 1359 1362 1831
		f 3 -3790 -3866 -5207
		mu 0 3 1361 1360 1395
		f 3 -3882 -3864 -3788
		mu 0 3 1357 1392 1360
		f 3 -3787 -5208 -5067
		mu 0 3 1358 1359 1831
		f 3 5208 -3785 -5066
		mu 0 3 1829 1345 1358
		f 3 -3780 -3885 -3883
		mu 0 3 1357 1356 1391
		f 3 -3736 -3776 -3782
		mu 0 3 1345 1346 1355
		f 3 -3734 -5209 -5059
		mu 0 3 1343 1345 1829
		f 3 -3773 -3741 -3732
		mu 0 3 1341 1348 1344
		f 3 -3730 -5058 -5051
		mu 0 3 1342 1343 1826
		f 3 -5049 5209 -3729
		mu 0 3 1342 1824 1339
		f 3 -3772 -3726 -3758
		mu 0 3 1354 1341 1340
		f 3 -3724 5210 -3761
		mu 0 3 1340 1338 1311
		f 3 -3722 -5210 -5046
		mu 0 3 1337 1339 1824
		f 3 5211 -3720 5212
		mu 0 3 1312 1338 1336
		f 3 -3718 -5045 -5091
		mu 0 3 1335 1337 1823
		f 3 -3716 5213 5214
		mu 0 3 1336 1333 1314
		f 3 -5098 -3714 -5090
		mu 0 3 1834 1334 1335
		f 3 -5099 5215 -3713
		mu 0 3 1334 1836 1332
		f 3 -5106 -3706 -5216
		mu 0 3 1836 1331 1332
		f 3 -5107 5216 -3705
		mu 0 3 1331 1839 1330
		f 3 -3708 -3700 -3665
		mu 0 3 1316 1329 1317
		f 3 -3663 -5214 -3711
		mu 0 3 1316 1314 1333
		f 3 -3661 -3670 -3690
		mu 0 3 1313 1315 1319
		f 3 -5215 -3659 -5213
		mu 0 3 1336 1314 1312
		f 3 -3655 -5211 -5212
		mu 0 3 1312 1311 1338
		f 3 -3653 5217 -3760
		mu 0 3 1311 1308 1353
		f 3 -3689 -3652 -3657
		mu 0 3 1313 1309 1310
		f 3 -3754 -5218 -3647
		mu 0 3 1307 1353 1308
		f 3 -3685 -3644 -3650
		mu 0 3 1309 1305 1306
		f 3 -3683 -3694 -3639
		mu 0 3 1305 1324 1304
		f 3 -3637 -3696 5218
		mu 0 3 1303 1304 1327
		f 3 -3618 -3641 -3634
		mu 0 3 1296 1295 1302
		f 3 -3616 -3763 -3646
		mu 0 3 1295 1294 1307
		f 3 -3614 5219 -3764
		mu 0 3 1294 1292 1262
		f 3 -3623 5220 -3612
		mu 0 3 1293 1298 1291
		f 3 -3627 -3607 -5221
		mu 0 3 1298 1290 1291
		f 3 -3602 5221 5222
		mu 0 3 1287 1289 1853
		f 3 5223 -3596 -5223
		mu 0 3 1853 1283 1287
		f 3 -5224 5224 -3585
		mu 0 3 1283 1853 1282
		f 3 -3580 5225 -3845
		mu 0 3 1279 1281 1386
		f 3 -3578 -3594 -3587
		mu 0 3 1280 1278 1284
		f 3 -3576 -3844 -3841
		mu 0 3 1277 1279 1384
		f 3 -3574 5226 -3595
		mu 0 3 1278 1275 1286
		f 3 -3572 -3840 -3890
		mu 0 3 1276 1277 1385
		f 3 -3570 -3888 -3886
		mu 0 3 1274 1276 1390
		f 3 -3568 5227 -5227
		mu 0 3 1275 1271 1286
		f 3 -3566 -3887 -3778
		mu 0 3 1273 1274 1356
		f 3 -3565 -3774 -3747
		mu 0 3 1272 1273 1347
		f 3 5228 -3563 -3746
		mu 0 3 1350 1269 1272
		f 3 -3560 -3593 -5228
		mu 0 3 1271 1270 1286
		f 3 -3558 5229 -3591
		mu 0 3 1270 1267 1285
		f 3 -5229 -3770 -3556
		mu 0 3 1269 1350 1268
		f 3 -3554 -3769 5230
		mu 0 3 1265 1268 1261
		f 3 -3552 -3598 -5230
		mu 0 3 1267 1266 1285
		f 3 -3609 -3601 -3550
		mu 0 3 1264 1288 1266
		f 3 -3546 -5220 -3610
		mu 0 3 1264 1262 1292
		f 3 -3549 -5231 -3545
		mu 0 3 1263 1265 1261
		f 3 -3543 -3768 -3765
		mu 0 3 1262 1261 1351;
	setAttr ".cd" -type "dataPolyComponent" Index_Data Edge 0 ;
	setAttr ".cvd" -type "dataPolyComponent" Index_Data Vertex 0 ;
	setAttr ".pd[0]" -type "dataPolyComponent" Index_Data UV 0 ;
	setAttr ".hfd" -type "dataPolyComponent" Index_Data Face 0 ;
	setAttr ".ndt" 0;
	setAttr ".vcs" 2;
createNode lightLinker -s -n "lightLinker1";
	rename -uid "77E0E847-4DF3-D1F7-04D3-DAB87AC0378A";
	setAttr -s 2 ".lnk";
	setAttr -s 2 ".slnk";
createNode displayLayerManager -n "layerManager";
	rename -uid "AB534529-4CF4-E10B-6104-8A8E9F9644CB";
createNode displayLayer -n "defaultLayer";
	rename -uid "BC789204-4DAD-119E-32C8-93A72643A18F";
	setAttr ".ufem" -type "stringArray" 0  ;
createNode renderLayerManager -n "renderLayerManager";
	rename -uid "A9367825-4631-2733-D357-64BCD21D3802";
createNode renderLayer -n "defaultRenderLayer";
	rename -uid "D9A6C494-41DC-7D59-9724-798FE202BE29";
	setAttr ".g" yes;
createNode skinCluster -n "Skirt_skinCluster";
	rename -uid "0AAA45B7-460C-FC9B-9ADE-2598CEB273CC";
	setAttr -s 1854 ".wl";
	setAttr ".wl[0:134].w"
		4 63 0.0049897003268303307 71 0.51087205935995206 77 0.43749141122691354 
		78 0.046646829086304076
		4 63 0.0030365453970346338 71 0.48822767190378563 77 0.45014113785187826 
		78 0.058594644847301473
		4 1 0.0038757914904710518 71 0.52564280270595609 77 0.43408863948217735 
		78 0.036392766321395577
		4 1 0.0095979242966100983 71 0.57236592522460972 77 0.39076827973989436 
		78 0.02726787073888582
		4 1 0.007232776387454164 71 0.51978331876888406 77 0.42378881632879678 
		78 0.049195088514865037
		4 63 0.0052185855773685813 71 0.48329899547717664 77 0.4434729592914225 
		78 0.068009459654032253
		4 63 0.0061341266839303101 71 0.47824825923509029 77 0.43854429480605012 
		78 0.077073319274929317
		4 63 0.0037537193944531481 71 0.47357899060840486 77 0.44672313436568512 
		78 0.075944155631456886
		4 63 0.0015564202773112976 71 0.4852979321047543 77 0.45597009165872615 
		78 0.057175555959208361
		4 1 0.0017547875491712803 71 0.50173188155362269 77 0.45261312342509874 
		78 0.043900207472107371
		4 1 0.0011596856476782963 71 0.51099412919496001 77 0.4529488023424223 
		78 0.034897382814939371
		4 1 0.002822918991735254 71 0.53868924455173717 77 0.43071641625516094 
		78 0.027771420201366675
		4 1 0.0059967957446844036 71 0.57770656651616259 77 0.39392691245321737 
		78 0.022369725285935713
		4 1 0.0052033267298914714 71 0.60271609194358322 77 0.37622645725074405 
		78 0.015854124075781375
		4 1 0.01115434552759088 71 0.64196230655065234 77 0.33243305357929831 
		78 0.014450294342458474
		4 1 0.020614938215293841 71 0.65444419878742643 77 0.3104753106602145 
		78 0.014465552337065224
		4 1 0.020935378861478917 71 0.72196536886430385 77 0.24945448211208018 
		78 0.0076447701621370056
		4 1 0.0093842988544305603 71 0.67707331123512204 77 0.30453956637690982 
		78 0.0090028235335376326
		4 1 0.014389257837861987 71 0.73817044290293821 77 0.24213015965522222 
		78 0.0053101396039776328
		4 1 0.041382468755095395 63 0.0061188679407482511 71 0.77274738842682689 
		77 0.17975127487732942
		4 1 0.037064165049531334 63 0.0094758524069369424 71 0.71905088759516778 
		77 0.23440909494836393
		4 1 0.06562904940215071 63 0.011490043124295289 71 0.74949263688743895 
		77 0.17338827058611508
		4 1 0.078400855191024091 63 0.0075074385267120333 71 0.78712138948100752 
		77 0.12697031680125642
		4 1 0.048996719116900851 63 0.0035095749390009227 71 0.81458763030326453 
		77 0.13290607564083373
		4 1 0.096498054999437768 63 0.0044403755003498985 71 0.81518272647674361 
		77 0.083878843023468666
		4 1 0.054108491845848448 63 0.0019226367164571184 71 0.85397116460993672 
		77 0.089997706827757776
		4 1 0.027954528739580254 71 0.82531471924286515 77 0.14491492837126088 
		78 0.0018158236462936955
		4 1 0.01455710769743309 71 0.84136720509721319 77 0.14264133911333432 
		78 0.0014343480920194428
		4 1 0.014648660979900679 71 0.77740138570046624 77 0.20485237188325819 
		78 0.0030975814363748311
		4 1 0.025726711359531588 71 0.78149080221902756 77 0.18919661627905679 
		78 0.0035858701423840574
		4 1 0.0078126190455780099 71 0.71337454016234059 77 0.27354847811642963 
		78 0.0052643626756517584
		4 1 0.003753719375225568 71 0.7076371292370266 77 0.28436714331330598 
		78 0.0042420080744419025
		4 1 0.0018768596618303479 71 0.63559930465939674 77 0.35551994451277052 
		78 0.0070038911660024262
		4 1 0.0018310825930706674 71 0.71421377520610063 77 0.28065919353330149 
		78 0.0032959486675272014
		4 1 0.0034332800114902111 71 0.79833676419733879 77 0.19645990920746939 
		78 0.00177004658370162
		4 1 0.0010528724682175236 71 0.72478827894936038 77 0.27061875564580673 
		78 0.0035400929366154413
		3 71 0.6254215263777283 77 0.36507210271459856 78 0.0095063709076731312
		3 71 0.68015564881584079 77 0.31143662971593983 78 0.0084077214682194146
		3 71 0.57607383716257698 77 0.39984742626235203 78 0.024078736575070959
		3 71 0.59406424453950291 77 0.38348973368838035 78 0.022446021772116746
		3 71 0.53311969239949375 77 0.41400779373219071 78 0.052872513868315506
		3 71 0.53702601010831486 77 0.41884489583706058 78 0.044129094054624569
		3 71 0.60735484353164537 77 0.37563134709048696 78 0.017013809377867724
		3 71 0.69466697263965604 77 0.29669642061577189 78 0.0086366067445720601
		3 71 0.70908675035476698 77 0.2846570508933659 78 0.0062561987518671416
		3 71 0.78742657276912809 77 0.20910962934096966 78 0.0034637978899022584
		4 1 0.0010528724964087351 71 0.78072785276868018 77 0.21545739180954901 
		78 0.0027618829253620446
		4 1 0.0014038299785420606 71 0.8423437858430034 77 0.1550164034364773 
		78 0.001235980741977249
		4 1 0.0012664988242080369 71 0.8636301208117797 77 0.13380636349584737 
		78 0.0012970168681648571
		3 1 0.0020599680136088585 71 0.90798809702195216 77 0.089951934964438929
		3 1 0.0031586175443829266 71 0.89076066369724727 77 0.10608071875836984
		3 1 0.006164644907984039 71 0.93823147781244132 77 0.055603877279574658
		3 1 0.0035706111013805754 71 0.95280384440605992 77 0.043625544492559468
		3 1 0.0070191501558282896 71 0.9734035252167339 77 0.019577324627437834
		3 1 0.0025177386000583622 71 0.9605401707414204 77 0.036942090658521304
		3 1 0.0016479743352983962 71 0.92095826426687932 77 0.077393761397822322
		3 1 0.0013122758858657346 71 0.92607003666011167 77 0.072617687454022667
		3 71 0.87809567498663488 77 0.12056153110427648 78 0.0013427939090886016
		3 71 0.80027466695647009 77 0.19653619748048592 78 0.0031891355630440394
		3 1 0.0016327153870434733 71 0.96278324365747148 77 0.035584040955485029
		3 1 0.0047455559620447393 71 0.97938506153511717 77 0.015869382502838144
		3 1 0.0028381780047216087 71 0.98281834175636273 77 0.014343480238915657
		3 1 0.0086213470324152039 71 0.98358129264176186 77 0.0077973603258229005
		3 1 0.0055848019764818124 71 0.98785381865224176 77 0.0065613793712764462
		3 1 0.013015945817804263 71 0.98234531139275494 77 0.0046387427894408126
		3 1 0.012329289965241179 71 0.97805752556154557 77 0.0096131844732132068
		3 1 0.012726024546762586 71 0.96002136319845877 77 0.027252612254778683
		3 1 0.023483633492026878 71 0.96339360796096463 77 0.013122758547008553
		3 1 0.018982223927732536 71 0.97581444943929552 77 0.0052033266329719599
		3 1 0.039520867665793477 71 0.95399404771525387 77 0.0064850846189527236
		3 1 0.030899519669139303 71 0.96603341687392441 77 0.0030670634569362767
		3 1 0.020675973918577718 71 0.97636377584104483 77 0.0029602502403774994
		3 1 0.0094758520980593158 71 0.98644998893747138 77 0.004074158964469313
		3 1 0.014053558649354139 71 0.98304722724900084 77 0.002899214101645068
		3 1 0.038132293929313339 71 0.95902952807918129 77 0.0028381779915053131
		3 1 0.024261845400035519 71 0.97302204868907227 77 0.0027161059108922097
		4 1 0.073624781321416852 63 0.0012664988009125381 71 0.92115663302512496 
		77 0.0039520868525456691
		4 1 0.079179061503661455 63 0.0011749446570479337 71 0.91628900910486799 
		77 0.0033569847344226676
		4 1 0.12791638323503077 63 0.0024872206166478132 71 0.86456091882627373 
		77 0.0050354773220477201
		4 1 0.15184252314092819 63 0.00270084693734158 71 0.84087892324826996 
		77 0.0045777066734603048
		4 1 0.21686122296027721 63 0.0055695433457235511 71 0.7709315587923784 
		77 0.0066376749016208202
		4 1 0.21313801730376927 63 0.0037994965088943189 71 0.77810330376418191 
		77 0.0049591824231545577
		4 1 0.15519951193593726 63 0.001800564572910286 71 0.83953612554157087 
		77 0.0034637979495816518
		4 1 0.22871747181608454 63 0.0028534370402040891 71 0.76420234192619341 
		77 0.0042267492175179795
		4 1 0.16984817539902378 63 0.0015411612252018618 71 0.82488746200003915 
		77 0.003723201375735191
		4 1 0.25571069681011266 63 0.0029602503120581456 71 0.73597313584328505 
		77 0.0053559170345440976
		4 1 0.30969711993962007 63 0.0049286642813651622 71 0.68024718444679311 
		77 0.0051270313322216675
		4 1 0.27542534047316936 63 0.0054169529216552869 71 0.71381704902464405 
		77 0.0053406575805313421
		4 1 0.34326695213012653 63 0.0083009076238297098 71 0.64275578429739555 
		77 0.0056763559486482573
		4 1 0.31198596547562302 63 0.0096284429218636818 71 0.67154954988351678 
		77 0.006836041718996517
		4 1 0.25972381149508678 63 0.0071107041790266848 71 0.72640573741642755 
		77 0.0067597469094590155
		4 1 0.29088273238088846 63 0.010498206915824577 71 0.69065385092067744 
		77 0.0079652097826095787
		4 1 0.25088882259362322 63 0.0081940944627367368 71 0.73296713282937453 
		77 0.0079499501142654555
		4 1 0.22203402903594352 63 0.0066987110497965146 71 0.76339360437541171 
		77 0.0078736555388482597
		4 1 0.18683146323104594 63 0.0046692607949708935 71 0.8018310830372235 
		77 0.0066681929367596697
		4 1 0.19810788093562942 63 0.0056000611998133403 71 0.78841840266302299 
		77 0.0078736552015342583
		4 1 0.16404974674498332 63 0.0039978637881298486 71 0.82510108831470386 
		77 0.0068513011521829439
		4 1 0.11648737717842077 63 0.0023651484094069581 71 0.87566948528271515 
		77 0.0054779891294570839
		4 1 0.14288547468737844 63 0.0035095749945662103 71 0.84660105911780781 
		77 0.0070038912002475563
		4 1 0.092484931682210988 63 0.0019226368212069279 71 0.90037384583902047 
		77 0.0052185856575616618
		3 1 0.048935680373762239 71 0.94749370859136495 77 0.0035706110348727627
		4 1 0.17676051430187623 63 0.0048523690908146271 71 0.81033035283388111 
		77 0.0080567637734280592
		4 1 0.34033722572908021 63 0.013824674661355922 71 0.63796444410738018 
		77 0.0078736555021836924
		4 1 0.37143510095766613 63 0.013504233966526318 71 0.60817884605889783 
		77 0.0068818190169097236
		4 1 0.3932097230549268 63 0.018020905436811653 71 0.58101778843707896 
		77 0.0077515830711824057
		4 1 0.43721676687182426 63 0.019165331854770554 71 0.53665978716052676 
		77 0.0069581141128784814
		4 1 0.42096590799761047 63 0.013839933025464728 71 0.55921262242266623 
		77 0.0059815365542586121
		4 1 0.39887082948229119 63 0.0093537802747802826 71 0.58611429283501859 
		77 0.0056610974079100177
		4 1 0.47269397533783714 63 0.013717860787009255 71 0.50719463352864014 
		77 0.0063935303465134435
		4 1 0.48694589915478936 63 0.014633402282869079 71 0.48986038748122906 
		77 0.0085603110811125899
		4 1 0.57540244721475908 63 0.026718547965862573 71 0.38849470598242741 
		77 0.0093842988369509401
		4 1 0.51860839128494263 63 0.025101091712713242 71 0.44040587544441223 
		77 0.0158846415579319
		4 1 0.60376898072818552 63 0.034912640725885603 71 0.35071335851218455 
		77 0.010605020033744311
		4 1 0.56008238852208214 63 0.024841689128615466 71 0.40823988038837644 
		77 0.0068360419609258018
		4 1 0.61554894595741394 63 0.036102844953526787 71 0.34110017372024548 
		77 0.0072480353688137798
		4 1 0.57091630887596312 63 0.031158922994632271 71 0.39159227365758187 
		77 0.0063324944718227312
		4 1 0.49355306417012718 63 0.018539711530837274 71 0.4819562058577001 
		77 0.0059510184413354636
		4 1 0.50121308960136501 63 0.022781721106337867 71 0.46967269477329365 
		77 0.0063324945190034931
		4 1 0.44386967582569309 63 0.022293431466369862 71 0.52623789987946124 
		77 0.0075989928284758475
		4 1 0.50548560957264377 63 0.026215000871557304 71 0.46138705219615178 
		77 0.0069123373596472332
		4 1 0.54848552746276169 63 0.029419394744260422 71 0.41559473434844735 
		77 0.0065003434445305699
		4 1 0.56878005398847065 63 0.03373769607883513 71 0.39089035259763982 
		77 0.0065918973350544028
		4 1 0.60405891768039854 63 0.038879986617043692 71 0.35057601120439907 
		77 0.0064850844981586102
		4 1 0.5233234167098999 63 0.031876098364591599 71 0.42606240510940552 
		77 0.018738079816102982
		4 1 0.41336690070622167 63 0.023437856885709676 71 0.53382162549538981 
		77 0.029373616912678837
		4 1 0.36371404982650235 63 0.013824674699981618 71 0.59530021478823081 
		77 0.027161060685285256
		4 1 0.32791637519220029 63 0.023437857016678904 71 0.60018311365961363 
		77 0.048462654131507209
		4 1 0.41437400699473564 63 0.029633021920474942 71 0.52129395466669881 
		77 0.03469901641809061
		4 1 0.31902036605623235 63 0.027710384222480389 71 0.59411002201398877 
		77 0.059159227707298562
		4 1 0.24742503602481467 63 0.025955597083767486 71 0.64071107268730776 
		77 0.085908294204110058
		4 1 0.22473487006796669 63 0.019775692152503594 71 0.67492180308414473 
		77 0.080567634695385013
		4 1 0.26996261459695187 63 0.014679179841299668 71 0.66518653863974886 
		77 0.050171666921999619
		4 1 0.15199512427294312 63 0.0099641411840299468 71 0.75492484291458783 
		77 0.083115891628439159
		4 1 0.19690242473889003 63 0.0066224155232109637 71 0.75051498657725979 
		77 0.045960173160639224
		2 1 0.29936674432416188 63 0.006897077940664762;
	setAttr ".wl[134:279].w"
		2 71 0.67182422122244678 77 0.021911956512726559
		4 1 0.17468528116024262 63 0.0032043945363815053 71 0.79574273497543668 
		77 0.026367589327939246
		4 1 0.24812694783201381 63 0.0037232012517720158 71 0.73270772113427451 
		77 0.015442129781939672
		4 1 0.16940565300780519 63 0.001937895768246803 71 0.81553369247833973 
		77 0.013122758745608273
		4 1 0.17587548473864389 63 0.0016021972969148806 71 0.81623560095178471 
		77 0.0062867170126564833
		3 1 0.11218433238823432 71 0.88384832186412521 77 0.0039673457476405299
		3 1 0.1001449580042806 71 0.8970931590877198 77 0.0027618829079996683
		3 1 0.055634394715524983 71 0.94193942078482384 77 0.0024261844996512141
		3 1 0.060990312937837604 71 0.93550011192704874 77 0.0035095751351137102
		3 1 0.04290837140396745 71 0.95457388993031911 77 0.0025177386657135137
		4 1 0.090684367791783849 63 0.0010681315158575747 71 0.90536354559954313 
		77 0.0028839550928154516
		3 1 0.094346528802417562 71 0.89700160572860821 77 0.0086518654689741875
		3 1 0.052597846443967172 71 0.92913710378753323 77 0.018265049768499658
		4 1 0.10159456519365397 63 0.0013580529203483112 71 0.87362478353255302 
		77 0.023422598353444773
		4 1 0.056870375636288176 63 0.0010223544813607874 71 0.89555199226100735 
		77 0.046555277621343719
		4 1 0.10308995275494096 63 0.0025329976779040479 71 0.8449225571295873 
		77 0.049454492437567665
		3 1 0.029388876577114916 71 0.88288700416146404 77 0.087724119261421041
		3 1 0.02821393119503943 71 0.93357747619305276 77 0.038208592611907809
		3 1 0.013733119486399896 71 0.91296254143085032 77 0.073304339082749775
		3 1 0.0066071567340987257 71 0.8677805690441579 77 0.12561227422174343
		4 1 0.0073853666925757502 71 0.78194857663221673 77 0.20816357705210342 
		78 0.00250247962310418
		4 1 0.0018310826472148496 71 0.81733424365862961 77 0.17947662073080456 
		78 0.0013580529633510133
		4 1 0.26507973405569124 63 0.0033417257611420455 71 0.72254519931286487 
		77 0.0090333408703017846
		4 1 0.36317998559826037 63 0.0070344094009098671 71 0.61800563997315705 
		77 0.011779965027672796
		4 1 0.36945143307610284 63 0.0067597469251977774 71 0.61683070602190615 
		77 0.0069581139767932575
		4 1 0.45593956495025761 63 0.014541847753223619 71 0.51528191998371609 
		77 0.014236667312802752
		4 1 0.12213321257630759 63 0.014419775724779363 71 0.73937590307324941 
		77 0.1240711086256636
		4 1 0.16861219201647662 63 0.021026931076439288 71 0.69356832821463565 
		77 0.11679254869244847
		4 1 0.096665906806764207 63 0.016647592683064719 71 0.72451361192803421 
		77 0.16217288858213688
		4 1 0.055466544967887409 63 0.013626306584246866 71 0.71255053483281394 
		77 0.21835661361505174
		3 71 0.52054626913099589 77 0.39122606198249898 78 0.088227668886505115
		3 71 0.52762646269241664 77 0.36195925417481739 78 0.11041428313276594
		3 71 0.53459984064102173 77 0.40296024084091187 78 0.062439918518066406
		3 71 0.54645609855651855 77 0.31067368388175964 78 0.1428702175617218
		3 71 0.53315021792297212 77 0.40503548255335653 78 0.061814299523671325
		3 71 0.55922789423219665 77 0.41660181463885709 78 0.024170291128946302
		3 71 0.52275884346201584 77 0.44232851431641174 78 0.034912642221572407
		3 71 0.51990539803924762 77 0.41890592163253432 78 0.0611886803282179
		3 71 0.50260167939512668 77 0.44806590342472563 78 0.049332417180147636
		3 71 0.51039903975725887 77 0.4520485069450102 78 0.037552453297730881
		3 71 0.54589151726039298 77 0.43195238226705363 78 0.022156100472553442
		4 1 0.0011291676258765365 71 0.5549095897488322 77 0.42594033697868872 
		78 0.018020905646602605
		3 71 0.49457541660862508 77 0.45920500672465198 78 0.046219576666722932
		4 1 0.0022430762752181184 71 0.55619133930300735 77 0.42206455348176797 
		78 0.019501030940006575
		4 1 0.003830014492503823 71 0.62841230586980523 77 0.35790035103594392 
		78 0.0098573286017468228
		3 71 0.61579310091109629 77 0.37553977476660455 78 0.0086671243222991561
		3 71 0.54782939365379058 77 0.32747388130034416 78 0.12469672504586521
		3 71 0.56548409811431022 77 0.20630196919587301 78 0.22821393268981677
		3 71 0.54822612625697442 77 0.26323339735319312 78 0.18854047638983246
		3 71 0.57079422473907471 77 0.17163348197937012 78 0.25757229328155518
		3 71 0.561699858878555 77 0.22146944371656413 78 0.21683069740488087
		3 71 0.58326084290833535 77 0.14576943435921422 78 0.2709697227324504
		3 71 0.58866255598273043 77 0.18631265779863806 78 0.22502478621863148
		3 71 0.56403447878463508 77 0.25857938106594625 78 0.17738614014941873
		3 71 0.53762113246886234 77 0.31274890433626018 78 0.14962996319487745
		3 71 0.54653239657381469 77 0.33096817382401356 78 0.12249942960217169
		3 71 0.52841991973549007 77 0.39465934626250487 78 0.076920734002005067
		3 71 0.60090028791948935 77 0.11783016385264572 78 0.28126954822786487
		3 71 0.59383535827573652 77 0.091508351948174471 78 0.31465628977608895
		3 71 0.59609370091348068 77 0.077698936811858341 78 0.32620736227466102
		3 71 0.59575800312286609 77 0.06266879848632817 78 0.34157319839080574
		3 71 0.59517813615766368 77 0.082917527599893917 78 0.32190433624244236
		3 71 0.58840314780464331 77 0.11145189072335092 78 0.30014496147200581
		3 71 0.59230945729287099 77 0.097489890531006734 78 0.3102006521761223
		3 71 0.58147555589675903 77 0.14067292213439941 78 0.27785152196884155
		3 71 0.59645992073074039 77 0.064972914271258453 78 0.3385671649980011
		3 71 0.59913023557999112 77 0.048371100737568021 78 0.35249866368244082
		3 71 0.6014496155245187 77 0.049942780844227756 78 0.34860760363125359
		3 71 0.61403830231811785 77 0.035706111096727354 78 0.35025558658515482
		3 71 0.62951094615657943 77 0.032425422583804535 78 0.33806363125961608
		3 71 0.6435950266578323 77 0.028656442993840438 78 0.32774853034832729
		3 71 0.67637140314696065 77 0.022735942409216715 78 0.30089265444382268
		3 71 0.69350729822723645 77 0.021011672444380691 78 0.28548102932838287
		3 71 0.61045242947774758 77 0.037323568989578573 78 0.35222400153267386
		3 71 0.60756847752908894 77 0.045609215268115073 78 0.34682230720279594
		3 71 0.60289921173152961 77 0.072449835313851699 78 0.32465095295461871
		3 71 0.56925307856123031 77 0.21809719177935732 78 0.21264972965941237
		4 1 0.032623790690657357 71 0.66517127551393629 77 0.28905165626185619 
		78 0.013153277533550226
		4 1 0.017349507304197959 71 0.59284352041542765 77 0.36482795325460382 
		78 0.024979019025770557
		4 1 0.78121614347042123 63 0.16116578854457597 69 0.0039826049413775027 
		71 0.053635463043625285
		4 1 0.75681697194550979 63 0.19046310796643634 69 0.004135195104253365 
		71 0.048584724983800578
		4 1 0.77489889714497517 63 0.1694667064186812 69 0.0042267493543102089 
		71 0.051407647082033457
		4 1 0.78844892684948098 63 0.15164415481819155 69 0.0046234838492293512 
		71 0.055283434483098109
		4 1 0.76633859679916905 63 0.178866254635274 69 0.0052338448104204864 
		71 0.04956130375513644
		4 1 0.78202487276347621 63 0.15759517501957526 69 0.0062714583302054478 
		71 0.05410849388674311
		4 1 0.74686808020045303 63 0.19998474586742251 69 0.0074921800451629057 
		71 0.045654993886961551
		4 1 0.7599450775993225 63 0.18008696630402729 69 0.010467689250386747 
		71 0.049500266846263408
		4 1 0.70495154771330226 63 0.24350347418582216 69 0.012771801508043941 
		71 0.038773176592831665
		4 1 0.68525215173007281 63 0.24937819734109445 69 0.023086900622541665 
		71 0.042282750306291049
		4 1 0.60328067697466947 63 0.34341955952539055 69 0.024200808797794775 
		71 0.029098954702145338
		4 1 0.59179062918870196 63 0.36861220791757182 69 0.014572366452929031 
		71 0.025024796440797224
		4 1 0.6654764556381465 63 0.29301900299213551 69 0.0088654916769883678 
		71 0.03263904969272962
		4 1 0.5460593563098437 63 0.42304112443503888 69 0.0095674067192524845 
		71 0.021332112535865009
		4 1 0.61898222006601589 63 0.34653238817524196 69 0.0065918977156837512 
		71 0.027893494043058482
		4 1 0.51230639171571812 63 0.46227207736831899 69 0.0066529335392146059 
		71 0.018768597376748363
		4 1 0.40125122479511788 63 0.57698940962092293 69 0.0093080037771351466 
		71 0.01245136180682405
		4 1 0.43506523764196209 63 0.53537803639016102 69 0.015304799120385204 
		71 0.014251926847491754
		4 1 0.31677729333905447 63 0.66071564882130807 69 0.013839933283253572 
		71 0.0086671245563839268
		4 1 0.35063708220389206 63 0.61489278765275446 69 0.024444952880348484 
		71 0.010025177263004824
		4 1 0.47046616235313787 63 0.4878919675211239 69 0.024765392534757104 
		71 0.016876477590981147
		4 1 0.41684594439829925 63 0.52207219211703393 69 0.043320361202058483 
		71 0.017761502282608282
		4 1 0.53585105934794597 63 0.3877622768738781 69 0.044098574503889029 
		71 0.032288089274286891
		4 1 0.41608301425103866 63 0.46771953206836481 69 0.078644999543502916 
		71 0.037552454137093634
		4 1 0.31877622305207159 63 0.58634317467308761 69 0.075516902613610978 
		71 0.019363699661229732
		4 1 0.29124894629698639 63 0.53424888650235214 69 0.13035781632975557 
		71 0.044144350870905999
		4 1 0.21887540491110974 63 0.63569085842831641 69 0.12347600425070518 
		71 0.02195773240986865
		4 1 0.18712139059930522 63 0.56246280460632292 69 0.20325016899686243 
		71 0.047165635797509417
		4 1 0.13929961595814747 63 0.64850842831934163 69 0.18858624959627865 
		71 0.023605706126232247
		4 1 0.082322423993583888 63 0.62418554585688257 69 0.27080186495329045 
		71 0.022690165196243089
		4 1 0.05217059653093483 63 0.68711375550261 69 0.25180437926385196 
		71 0.008911268702603236
		4 1 0.028320744079783907 63 0.62343786927666955 69 0.33623253641567818 
		70 0.012008850227868319
		4 1 0.017990385560614313 63 0.65821317795567691 69 0.31436636077790531 
		70 0.0094300757058034673
		4 1 0.0089417873366819112 63 0.58321506056569083 69 0.38977647009201566 
		70 0.01806668200561163
		4 1 0.0072327764884948841 63 0.61725796217541806 69 0.36224917134001045 
		70 0.013260089996076641
		4 1 0.003479057001357126 63 0.55141526614711234 69 0.41950103757763574 
		70 0.025604639273894874
		4 1 0.0021210040377147858 63 0.54233616451600153 69 0.42824444065087269 
		70 0.027298390795411007
		4 1 0.0012817578664798578 63 0.50829328195261347 69 0.44431219456641047 
		70 0.046112765614496183
		4 1 0.0016174563169072933 63 0.53963529937985522 69 0.4328526844436939 
		70 0.025894559859543666
		4 1 0.0030518043928398023 63 0.59456777849499032 69 0.38814374985240285 
		70 0.014236667259767034
		4 1 0.0012207217218924641 63 0.54581521619931272 69 0.42911421213581274 
		70 0.023849849942982105
		3 63 0.51654840670261692 69 0.43408865706820765 70 0.049362936229175397
		3 63 0.53151750762580896 69 0.42175936856031182 70 0.046723123813879205
		3 63 0.53725491753395826 69 0.36180665280357033 70 0.10093842966247135
		3 63 0.53940641478146301 69 0.4093690484064143 70 0.051224536812122634
		3 63 0.57930875148237915 69 0.40157169328018105 70 0.019119555237439769
		3 63 0.58530556065392569 69 0.39197375640321974 70 0.022720682942854557
		3 63 0.5341115514321394 69 0.40227358933875579 70 0.063614859229104828
		3 63 0.53592736327539925 69 0.34608987489476611 70 0.11798276182983461
		3 63 0.53047990008473545 69 0.32823681342248895 70 0.14128328649277558
		3 63 0.53402000267788763 69 0.38760965773754075 70 0.078370339584571569
		3 63 0.58068207831502061 69 0.38971541932859838 70 0.029602502356381073
		3 63 0.56903945975721282 69 0.391454932157286 70 0.039505608085501132
		3 63 0.66593422056022611 69 0.32195011530886675 70 0.012115664130907136
		3 63 0.64170289218901533 69 0.34480813241975794 70 0.013488975391226753
		3 63 0.5707026783827992 69 0.39882505385754691 70 0.030472267759653938
		3 63 0.54328221082687378 69 0.37842375040054321 70 0.078294038772583008
		3 63 0.53659875000415369 69 0.39803159830021262 70 0.065369651695633704
		3 63 0.54959946870803833 69 0.2858930230140686 70 0.16450750827789307
		3 63 0.56929885492773569 69 0.28177308616380264 70 0.14892805890846164
		3 63 0.56247806549072266 69 0.18730449676513672 70 0.25021743774414062
		3 63 0.53382162648970999 69 0.16597237688385316 70 0.30020599662643682
		3 63 0.51927977026582106 69 0.1163500381059939 70 0.36437019162818501
		3 63 0.54535744949109999 69 0.12855726097353515 70 0.32608528953536481
		3 63 0.5074540263238394 69 0.089219501110475483 70 0.4033264725656851
		3 63 0.48827343451569327 69 0.07310597489616312 70 0.43862059058814362
		2 63 0.48291751382561388 69 0.066651410857950066;
	setAttr ".wl[279:423].w"
		1 70 0.450431075316436
		3 63 0.49005875539100269 69 0.050034333579625938 70 0.45990691102937137
		3 63 0.48934157406765588 69 0.056504154967035786 70 0.45415427096530836
		3 63 0.49787137283288962 69 0.042435340899492358 70 0.45969328626761796
		3 63 0.49643702424549363 69 0.10032806769746694 70 0.40323490805703943
		3 63 0.55985351085226265 69 0.13267720141044859 70 0.30746928773728871
		3 63 0.58237582445144653 69 0.18536660075187683 70 0.23225757479667664
		3 63 0.5830014434904075 69 0.18988326474850276 70 0.22711529176108974
		3 63 0.57950712977371011 69 0.26198215073293896 70 0.15851071949335097
		3 63 0.55387198099684742 69 0.28499275021265819 70 0.16113526879049436
		3 63 0.54818035397336673 69 0.35547418196814168 70 0.096345464058491523
		3 63 0.56926833735006543 69 0.18881512896992075 70 0.24191653368001381
		3 63 0.54810405594265543 69 0.21339743157323349 70 0.23849851248411108
		3 63 0.56173036808579058 69 0.15190356517125472 70 0.28636606674295467
		3 63 0.5723048788768853 69 0.14537269717278939 70 0.28232242395032536
		3 63 0.55165941345184166 69 0.15356679489563099 70 0.29477379165252732
		3 63 0.54845500809632253 69 0.18435950851976138 70 0.26718548338391607
		3 63 0.54421300506909198 69 0.24977493658326472 70 0.2060120583476433
		3 63 0.55442130565643311 69 0.21281757950782776 70 0.23276111483573914
		3 63 0.55161362886428833 69 0.27286183834075928 70 0.17552453279495239
		3 63 0.54250401258468628 69 0.29974821209907532 70 0.1577477753162384
		3 63 0.55397879251869331 69 0.24206912156836508 70 0.20395208591294162
		3 63 0.54042876572055765 69 0.27084765241813141 70 0.18872358186131094
		3 63 0.52298771555740065 69 0.32529183737498762 70 0.1517204470676117
		3 63 0.52127868713853787 69 0.38204014870584235 70 0.096681164155619809
		3 63 0.5037918649331341 69 0.4001220732918227 70 0.096086061775043141
		3 63 0.51099412871905969 69 0.34694438655757326 70 0.14206148472336702
		3 63 0.53563744627889165 69 0.28134584846117866 70 0.18301670525992966
		3 63 0.53733121548099494 69 0.29193558853960649 70 0.17073319597939854
		4 1 0.0010833905849350293 63 0.50533302061848706 69 0.37743190994236181 
		70 0.11615167885421615
		4 63 0.52429998152928892 69 0.33318075685073489 70 0.14085602822626581 
		71 0.0016632333937104406
		4 1 0.0019378957375651004 63 0.50246434292427433 69 0.41428243197574488 
		70 0.081315329362415645
		4 63 0.50284582235986608 69 0.39128708730092154 70 0.10080109508484296 
		71 0.0050659952543694658
		4 1 0.0059510185743510916 63 0.50772869894303063 69 0.43595025207258448 
		70 0.050370030410033836
		4 63 0.49030289510547087 69 0.42851910394168558 70 0.066163123270153279 
		71 0.015014877682690301
		4 1 0.021179523950204966 63 0.52137024764329942 69 0.42589457112236534 
		70 0.031555657284130373
		4 63 0.48957046319279302 69 0.43160143012253832 70 0.045258257032279779 
		71 0.033569849652388885
		4 1 0.058533608041202903 63 0.51853208961289987 69 0.3847714903239684 
		71 0.038162812021928845
		4 1 0.057114518540562854 63 0.48659493975421481 69 0.40534066700927168 
		71 0.050949874695950657
		4 63 0.46845197503100344 69 0.41818874918599147 70 0.066651411106245922 
		71 0.04670786467675915
		4 63 0.47209888344929463 69 0.40431829985739065 70 0.091355762695105647 
		71 0.032227053998209132
		4 63 0.4665446018170164 69 0.36395818266241386 70 0.12362859490237083 
		71 0.045868620618198963
		4 63 0.48888380063897074 69 0.32246891144616768 70 0.15651178593206086 
		71 0.032135501982800692
		4 63 0.49285114362296994 69 0.27362478085187952 70 0.19034104261928472 
		71 0.04318303290586583
		4 63 0.52440679854760763 69 0.22978560968914047 70 0.21745632912898555 
		71 0.028351262634266357
		4 63 0.52501715011920258 69 0.19594110840471252 70 0.24386969572111511 
		71 0.035172045754969801
		4 63 0.54715800285339355 69 0.1744869202375412 70 0.25584802031517029 
		71 0.022507056593894958
		4 63 0.5630579031458175 69 0.19458304472461466 70 0.23007553965833855 
		71 0.012283512471229385
		4 63 0.56800181467088617 69 0.1637445711122533 70 0.25551233052526129 
		71 0.012741283691599272
		4 63 0.58840314616066391 69 0.17933928381942685 70 0.22719157491651817 
		71 0.0050659951033910468
		4 63 0.5759517660429806 69 0.21675441082889718 70 0.20270085721776596 
		71 0.0045929659103563069
		4 63 0.59172960078201109 69 0.19917602000846965 70 0.2073395916341996 
		71 0.0017547875753196533
		4 63 0.56676584785702044 69 0.24490730595608895 70 0.18672464887953058 
		71 0.0016021973073600182
		3 63 0.56781870972840054 69 0.23524834566188374 70 0.19693294460971572
		4 63 0.53653771359777003 69 0.29842070120263797 70 0.16000610791154435 
		71 0.0050354772880477306
		4 63 0.53299762555855967 69 0.26767376937771398 70 0.18489356941662258 
		71 0.014435035647103793
		4 63 0.49686427081153428 69 0.36412603510837155 70 0.12391852130923703 
		71 0.015091172770857177
		4 63 0.54729533909087513 69 0.15637445653718188 70 0.27182421442637128 
		71 0.024505989945571738
		4 1 0.11152819172946261 63 0.5019149948553554 69 0.32828260568731821 
		71 0.058274207727863896
		4 1 0.1102922107640944 63 0.55040818247792056 69 0.29506370315304509 
		71 0.044235903604939938
		4 1 0.19424735588572489 63 0.50963605969059644 69 0.23166247402615767 
		71 0.064454110397520969
		4 1 0.30659952988177186 63 0.48284122707576471 69 0.1473868947281457 
		71 0.063172348314317672
		4 1 0.044647898441836427 63 0.57462423932808593 69 0.3608911328746171 
		71 0.019836729355460537
		4 1 0.013748378044745669 63 0.55335317238479753 69 0.40933852053540926 
		70 0.023559929035047521
		4 1 0.0040588998746081701 63 0.52411688033079529 69 0.43376821824896239 
		70 0.038056001545634141
		4 1 0.0016632333813183862 63 0.50759136523150661 69 0.43361562359216549 
		70 0.057129777795009523
		3 63 0.49687952173411487 69 0.41763943744927223 70 0.085481040816612841
		3 63 0.5075455904006958 69 0.44165712594985962 70 0.05079728364944458
		3 63 0.57740139746143893 69 0.4008544966546651 70 0.021744105883895956
		3 63 0.65595484390812786 69 0.33487448408151499 70 0.0091706720103572302
		3 63 0.75925840114035048 69 0.2378423846554005 70 0.0028992142042490042
		3 63 0.73740749864459509 69 0.25807583091709918 70 0.0045166704383057497
		2 63 0.85854886683003806 69 0.14145113316996197
		3 63 0.83891051421702945 69 0.15965513773503384 70 0.001434348047936698
		2 63 0.924605176976246 69 0.075394823023754012
		2 63 0.92610055898204857 69 0.073899441017951373
		2 63 0.96530098442212475 69 0.034699015577875192
		2 63 0.97335774794248209 69 0.026642252057517902
		2 63 0.93986419722741399 69 0.060135802772585983
		3 63 0.86964218350727185 69 0.12925916693483944 70 0.0010986495578887946
		2 63 0.93994049117102119 69 0.060059508828978786
		3 1 0.0014190890581996568 63 0.97372396319161769 69 0.024856947750182705
		3 1 0.0031280994727997833 63 0.96849011901340154 69 0.028381781513798655
		3 1 0.0068818192668682722 63 0.98204013011511715 69 0.011078050618014545
		3 1 0.014358739676187757 63 0.97012283495890461 69 0.015518425364907629
		3 1 0.016617074160002961 63 0.97479209651335075 69 0.0085908293266463553
		3 1 0.030655374179494117 63 0.95190356388867714 69 0.017441061931828747
		3 1 0.034912641538758851 63 0.95600824034573506 69 0.0090791181155061278
		3 1 0.05558861719608247 63 0.92503242478663672 69 0.019378958017280873
		3 1 0.044861524962920507 63 0.91755550416145093 69 0.037582970875628507
		4 1 0.090592816387682393 63 0.88297855771800637 69 0.025024795881449437 
		71 0.0014038300128617976
		4 1 0.11590752645386533 63 0.87032883569066777 69 0.011886778179652908 
		71 0.0018768596758140419
		3 1 0.069581143752432836 63 0.91841000575128018 69 0.012008850496287041
		4 1 0.13052568040198995 63 0.86071564089675257 69 0.0066224156033898307 
		71 0.0021362630978676873
		4 1 0.15728999341060654 63 0.82282750055256704 69 0.01690699683070725 
		71 0.0029755092061191477
		4 1 0.12379644998506859 63 0.84113831600965716 69 0.03288319384153178 
		71 0.0021820401637425205
		4 1 0.20692759424655782 63 0.76865797017963089 69 0.019851987867165549 
		71 0.0045624477066457166
		4 1 0.25595483100429001 63 0.7262684083153127 69 0.011535820513614107 
		71 0.0062409401667832482
		4 1 0.27905699896591435 63 0.6923475932477261 69 0.021469444256428525 
		71 0.0071259635299310078
		4 1 0.21660181526976474 63 0.74134432061247002 69 0.036835278715363351 
		71 0.0052185854024018674
		4 1 0.30057220643330418 63 0.65040055716929956 69 0.039765010185967786 
		71 0.0092622262114285085
		4 1 0.21847867925003417 63 0.70336460936187839 69 0.069275960197158232 
		71 0.0088807511909292057
		4 1 0.14926375594667107 63 0.78200960924020124 69 0.064499885474563382 
		71 0.0042267493385643399
		4 1 0.091828794741155129 63 0.79780269932248249 69 0.10652323235840998 
		71 0.0038452735779524322
		4 1 0.06492713935564666 63 0.82507057227299474 69 0.10804913353993198 
		71 0.0019531548314266627
		4 1 0.041489280470488964 63 0.80389105712139708 69 0.15269702566300733 
		70 0.0019226367451066378
		4 1 0.030090791985498865 63 0.79629206342227643 69 0.17128251425181451 
		70 0.0023346303404102298
		4 1 0.025055313348706764 63 0.75744258951833943 69 0.213855190920022 
		70 0.0036469062129317682
		4 1 0.055329214343523309 63 0.77732508759269192 69 0.16365301479487621 
		71 0.0036926832689085903
		4 1 0.032776378400403802 63 0.72756541452897172 69 0.23491265098482977 
		70 0.0047455560857947547
		4 1 0.014114594637115258 63 0.69040970129717016 69 0.28828870471532231 
		70 0.0071869993503922772
		4 1 0.015671014851443066 63 0.73488974879216762 69 0.24484627051447352 
		70 0.0045929658419157811
		4 1 0.0081788358489820155 63 0.66518653368372282 69 0.31816587296546261 
		70 0.0084687575018325464
		4 1 0.0041199359476001857 63 0.59853512578279122 69 0.38251316885824793 
		70 0.014831769411360668
		4 1 0.0054932479991993905 63 0.6495918174652493 69 0.33617151503632298 
		70 0.0087434194992283814
		4 1 0.0099336232817361942 63 0.71328298776203236 69 0.27171739379150545 
		70 0.0050659951647260282
		4 1 0.0047455560349688548 63 0.66367590334684234 69 0.32454413130244597 
		70 0.007034409315742912
		4 1 0.0023041122999635441 63 0.59056991187476815 69 0.39366751808432332 
		70 0.013458457740945035
		4 1 0.0019836728063887307 63 0.63190661595576236 69 0.35701533437163596 
		70 0.0090943768662129498
		3 63 0.56327153406289754 69 0.41657129783608815 70 0.020157168101014287
		3 63 0.65572595962728908 69 0.33684289643639453 70 0.0074311439363163555
		4 1 0.0040741589341144642 63 0.71309987167101807 69 0.27875181046075298 
		70 0.0040741589341144642
		4 1 0.0020599679200822428 63 0.75234608546048165 69 0.24261843740153957 
		70 0.0029755092178965726
		4 1 0.0061036089206847888 63 0.79481192571189518 69 0.19717708757970601 
		70 0.0019073777877139965
		4 1 0.0091401545277128779 63 0.75173570213316354 69 0.23590448965595143 
		70 0.0032196536831722044
		4 1 0.016601815931837228 63 0.82894635760212432 69 0.15294118328841735 
		70 0.0015106431776212184
		4 1 0.021515219917759221 63 0.79163805842658241 69 0.1843900191863459 
		70 0.0024567024693125535
		4 1 0.04127565437253243 63 0.85229266483609256 69 0.10533303120483674 
		70 0.0010986495865383146
		4 1 0.050965132488078088 63 0.83421072780252059 69 0.11354238190977033 
		71 0.0012817577996309779
		4 1 0.086533912594033729 63 0.84856946323397142 69 0.063263908809280761 
		71 0.0016327153627141179
		4 1 0.10917830314703794 63 0.82368199866709313 69 0.064759290803792544 
		71 0.002380407382076503
		4 1 0.16145570369435855 63 0.79951172043263341 69 0.035751886207993668 
		71 0.0032806896650144058
		4 1 0.068177314231657904 63 0.87681390937301762 69 0.053879608748415506 
		71 0.0011291676469089231
		3 1 0.030075531564934296 63 0.88686961265977327 69 0.083054855775292424
		3 1 0.017578393286386107 63 0.92597848521910042 69 0.056443121494513457
		3 1 0.010452429656892338 63 0.87428092060881657 69 0.11526664973429111
		3 1 0.0054322117888999993 63 0.92593270454003229 69 0.06863508367106777
		3 1 0.0032806896894574484 63 0.85874723928254415 69 0.13797207102799844
		3 1 0.0012359807868700234 63 0.86379797211813381 69 0.13496604709499613
		3 63 0.77154193368588364 69 0.22583351461449183 70 0.0026245516996244939
		3 63 0.78083466410887303 69 0.21631189883630675 70 0.0028534370548201756
		3 63 0.67670709398915685 69 0.3140154206306891 70 0.0092774853801539936
		3 63 0.77328144801827692 69 0.22319371795641374 70 0.0035248340253092986
		2 63 0.87444876321481524 69 0.12555123678518479
		2 63 0.67287707642129191 69 0.31963074356145571;
	setAttr ".wl[423:560].w"
		1 70 0.0074921800172523595
		3 1 0.0017853056059749098 63 0.93150224622123423 69 0.066712448172790914
		3 1 0.0088960100131035037 63 0.96104371726707316 69 0.030060272719823332
		3 1 0.02189669612602696 63 0.95043869596791819 69 0.027664607906054853
		4 1 0.088532842530807773 63 0.72634470327506828 69 0.17573815551448957 
		71 0.0093842986796343723
		4 1 0.14258029871049879 63 0.73368429181018835 69 0.1145952552516632 
		71 0.009140154227649645
		4 1 0.30173188686810531 63 0.68316168133809629 69 0.0075074388308573794 
		71 0.0075989929629410062
		4 1 0.23930723753439379 63 0.74937056832106752 69 0.0061951628338042207 
		71 0.0051270313107345273
		4 1 0.31252001813787916 63 0.6738689347264013 69 0.0058289461948933712 
		71 0.0077821009408262287
		4 1 0.2327763718904825 63 0.75698482426267244 69 0.005249103492132548 
		71 0.0049897003547124535
		4 1 0.29884794674511195 63 0.68818188450680273 69 0.0054932479403655525 
		71 0.0074769208077197797
		4 1 0.22252232364781133 63 0.76733042631943327 69 0.0052491036559009392 
		71 0.0048981463768544911
		4 1 0.27348744601791891 63 0.71416800515841328 69 0.005600061212851999 
		71 0.0067444876108159121
		4 1 0.16327153298325403 63 0.82856488999505429 69 0.0049286643502178071 
		71 0.0032349126714739268
		4 1 0.1662012686580335 63 0.82601662970989598 69 0.0046845200947260232 
		71 0.0030975815373444973
		4 1 0.11366445777607795 63 0.88021667410081739 69 0.0041657132853115059 
		71 0.0019531548377932227
		4 1 0.11641107215006775 63 0.87711910249257796 69 0.0045929657103816511 
		71 0.0018768596469726732
		4 1 0.071595334916843126 63 0.92333866971555356 69 0.0039673457698098024 
		71 0.0010986495977934837
		4 1 0.085038529192707504 63 0.9072098875628487 69 0.0065003434293957781 
		71 0.0012512398150480136
		4 1 0.1737697452444027 63 0.8175936482152738 69 0.0054627299318653569 
		71 0.0031738766084580842
		4 1 0.19067673429538667 63 0.79679560846834352 69 0.0087129017541019756 
		71 0.0038147554821678334
		3 1 0.047989626310587008 63 0.94654764375754763 69 0.0054627299318653569
		3 1 0.043625544685549376 63 0.9530937656127717 69 0.00328068970167897
		4 1 0.077668420156678436 63 0.91725032560614295 69 0.003768978368117468 
		71 0.0013122758690611426
		3 1 0.062745101603807182 63 0.93368428728151065 69 0.0035706111146821384
		4 1 0.12156862844804339 63 0.87153429361129187 69 0.004638742685756831 
		71 0.0022583352549079309
		4 1 0.20588998113032467 63 0.78411535948300071 69 0.0054474709472158746 
		71 0.0045471884394588241
		4 1 0.15744258078479417 63 0.83413443910327845 69 0.0052338446142259788 
		71 0.0031891354977015341
		4 1 0.10193026977011908 63 0.89181353115172757 69 0.0044861525097001989 
		71 0.0017700465684531395
		4 1 0.13122758712340149 63 0.86123445557407019 69 0.0050812546947928919 
		71 0.0024567026077354976
		4 1 0.10328832232641875 63 0.89062332795948029 69 0.0045166704645962326 
		71 0.00157167924950477
		3 1 0.062699318194898712 63 0.93366903457931305 69 0.0036316472257882475
		4 1 0.11116197637975882 63 0.88259708347089494 69 0.0047455560128706374 
		71 0.0014953841364756255
		4 1 0.12927442906464048 63 0.86352331230356572 69 0.0050812545693872798 
		71 0.0021210040624065228
		4 1 0.14044404160644897 63 0.8523689587821156 69 0.0052033267468523867 
		71 0.001983672864583068
		4 1 0.11552605549345847 63 0.87780575207120526 69 0.0051575492978115358 
		71 0.0015106431375246805
		3 1 0.066681928280591732 63 0.92927443072443683 69 0.0040436409949714033
		3 1 0.069321736983906312 63 0.92607003838505142 69 0.0046082246310422299
		3 1 0.034943159946256186 63 0.96142519281442662 69 0.0036316472393171876
		3 1 0.035385671755864712 63 0.96049439236176393 69 0.0041199358823713669
		3 1 0.018310826706631183 63 0.97811856208557568 69 0.0035706112077930809
		3 1 0.018036163948616148 63 0.97906462195513899 69 0.0028992140962448613
		3 1 0.0093995572870225388 63 0.9868925004715059 69 0.0037079422414715534
		3 1 0.016250857969856414 63 0.97999542267064976 69 0.003753719359493912
		3 1 0.0069886321328256947 63 0.98927290744677632 69 0.0037384604203980249
		3 1 0.0043793394203162968 63 0.99078355051259193 69 0.0048371100670918012
		3 1 0.011413748546149559 63 0.98535133876430003 69 0.0032349126895504102
		3 1 0.0068207830571799521 63 0.98866254643721074 69 0.0045166705056093846
		3 1 0.0019226367648031829 63 0.98850995624417892 69 0.0095674069910179124
		3 1 0.0030365453447165733 63 0.99192797745047712 69 0.0050354772048063776
		3 1 0.0014343480612951053 63 0.98841840258896918 69 0.010147249349735793
		3 1 0.0020904860212634948 63 0.99287403670124053 69 0.0050354772774960097
		3 1 0.0050659952343176445 63 0.9917448692115487 69 0.0031891355541336978
		3 1 0.013122758702832948 63 0.98374914183893358 69 0.0031280994582334352
		3 1 0.0010833905778721263 63 0.98580910909926689 69 0.013107500322861022
		3 1 0.0010223544451793995 63 0.9752040894833458 69 0.023773556071474775
		3 1 0.0030823223635669719 63 0.98706034921599817 69 0.0098573284204348625
		3 1 0.0096894792748493403 63 0.9853360795161773 69 0.0049744412089733764
		3 1 0.011627375299840471 63 0.98525978419337146 69 0.0031128405067881262
		3 1 0.016693369996993813 63 0.97885099572224832 69 0.0044556342807578614
		3 1 0.026108187245168966 63 0.97015335231180189 69 0.0037384604430291571
		3 1 0.01844815678497393 63 0.97885099640596784 69 0.0027008468090582373
		3 1 0.033066298489276197 63 0.9640955234663533 69 0.0028381780443704971
		3 1 0.032608531149733208 63 0.96441595960535142 69 0.0029755092449153717
		3 1 0.032791636212341491 63 0.96342412643569453 69 0.0037842373519640215
		3 1 0.069428548410800886 63 0.92588693162208502 69 0.0046845199671141429
		4 1 0.11761654214921435 63 0.87533378947541918 69 0.005447471070244677 
		71 0.0016021973051217743
		4 1 0.15288014464342733 63 0.83923094116455532 69 0.005828946269537021 
		71 0.002059967922480361
		4 1 0.14897383607273751 63 0.84356450229274471 69 0.0054932478290928618 
		71 0.001968413805424942
		4 1 0.35582512617111206 63 0.62854963541030884 69 0.0056153200566768646 
		71 0.010009918361902237
		4 1 0.38747232448709168 63 0.59574275126961651 69 0.0055695431226807732 
		71 0.011215381120611045
		4 1 0.44454109192618863 63 0.53525596283800569 69 0.0054627297792384467 
		71 0.014740215456567259
		4 1 0.48282597255842252 63 0.49483481856026623 69 0.0055237660153451421 
		71 0.016815442865966122
		4 1 0.40489813195199176 63 0.57674526469997278 69 0.006332494241816527 
		71 0.012024109106218985
		4 1 0.57880521871773694 63 0.39111924881751214 69 0.0054016938482718824 
		71 0.024673838616479052
		4 1 0.53560692595678638 63 0.43764400910144868 69 0.0052185855384870878 
		71 0.021530479403277892
		4 1 0.6232547580069886 63 0.3416189750747865 69 0.0049439229506425455 
		71 0.030182343967582414
		4 1 0.66543068453768883 63 0.29541466506716046 69 0.0051575495511878384 
		71 0.033997100843962909
		4 1 0.7069657448245984 63 0.24824902426835571 69 0.0060578319272295723 
		71 0.038727398979816308
		4 1 0.7355611457894019 63 0.21593042110152841 69 0.004669260784099424 
		71 0.043839172324970234
		4 1 0.70048064580590075 63 0.25526818847042854 69 0.0045624478171225917 
		71 0.03968871790654814
		4 1 0.44167238309356427 63 0.41573205435375848 69 0.087693601520010822 
		71 0.05490196103266641
		4 1 0.57802700565735254 63 0.32753491157639836 69 0.048432133731006577 
		71 0.046005949035242577
		3 63 0.53092241089447434 69 0.047013047907452851 70 0.4220645411980728
		3 63 0.51395438761383028 69 0.056305790714396037 70 0.42973982167177366
		3 63 0.51537347223887942 69 0.077805750651700423 70 0.40682077710942011
		3 63 0.5234149694442749 69 0.072129398584365845 70 0.40445563197135925
		3 63 0.53788052987529844 69 0.042267489391053292 70 0.41985198073364832
		3 63 0.56650644646306791 69 0.027267871475346147 70 0.40622568206158594
		3 63 0.58870833125268107 69 0.016723887714529428 70 0.39456778103278944
		3 63 0.64654002225486484 69 0.010162508677376584 70 0.3432974690677586
		3 63 0.58762491898622671 69 0.012405584808920771 70 0.3999694962048525
		3 63 0.64991225325298152 69 0.0082398720141470434 70 0.34184787473287143
		4 63 0.69146257043254655 69 0.0077973603530548672 70 0.29822233062371933 
		71 0.002517738590679055
		4 63 0.63616387673488894 69 0.011886778032969782 70 0.34877546874635312 
		71 0.003173876485788115
		4 63 0.7026016672927794 69 0.0085450522124112457 70 0.27943846427217983 
		71 0.0094148162226296052
		4 63 0.70853741725556696 69 0.0063324944747715287 70 0.2833295236418325 
		71 0.001800564627828973
		4 63 0.73379111563336519 69 0.0064087892189949348 70 0.25278094505064541 
		71 0.0070191500969944524
		4 63 0.71528190507606026 70 0.24870680318904445 71 0.024292362899132749 
		78 0.011718928835762532
		4 63 0.67290760277327566 70 0.28133059045791742 71 0.030182345373057352 
		78 0.015579461395749604
		4 63 0.65131610267991513 70 0.25273516632950771 71 0.064774550135575884 
		78 0.031174180855001243
		4 63 0.6014190889842097 70 0.28699168455976365 71 0.073365375126282217 
		78 0.038223851329744415
		4 63 0.5557335656563458 70 0.25145343133399956 71 0.12980850137627498 
		78 0.063004501633379617
		4 63 0.5062638332596483 70 0.2827954484971073 71 0.13730067993325443 
		78 0.073640038309989928
		4 63 0.5421225307407409 70 0.34879072721025212 71 0.066987103216638338 
		78 0.042099638832368579
		4 63 0.60410468532675587 69 0.020798045715729702 70 0.34563209898406067 
		71 0.029465169973453751
		4 63 0.5331349452307067 69 0.038086519212819921 70 0.40140385033792036 
		71 0.027374685218553026
		4 63 0.56270695047103025 69 0.026642251908642715 70 0.40053406581581047 
		71 0.01011673180451653
		4 63 0.52849622081884629 69 0.038666361178573236 70 0.42835126543856561 
		71 0.0044861525640149166
		4 63 0.58060579275374269 69 0.018875410384780977 70 0.39658196929554052 
		71 0.0039368275659357943
		4 63 0.63624017601147065 69 0.014007782380926466 70 0.33952849660683521 
		71 0.01022354500076768
		4 63 0.60634774830825922 69 0.015533684973501317 70 0.37703517614843923 
		71 0.0010833905698002374
		4 63 0.55957883987281587 69 0.024963760922875448 70 0.41359579852034195 
		71 0.0018616006839666562
		4 63 0.51451896531013175 69 0.061371783356919819 70 0.42149995864450551 
		71 0.002609292688442945
		4 63 0.50701152995036058 69 0.05510032891239787 70 0.42433812977184654 
		71 0.013550011365394975
		4 63 0.49558252488491261 69 0.081681542745133034 70 0.41495383114284606 
		71 0.0077821012271082589
		4 63 0.47890439272743168 69 0.068375676360907578 70 0.4112611680383893 
		71 0.041458762873271382
		4 63 0.49929045328858057 69 0.046082245846928209 70 0.39563592236693407 
		71 0.058991378497557159
		4 63 0.44615853830036234 70 0.37581444626631838 71 0.097215229955655999 
		78 0.080811785477663253
		4 63 0.46463722336767033 70 0.33495077740364354 71 0.1203936868935353 
		78 0.080018312335150776
		4 63 0.38927290423621097 70 0.29578087174565898 71 0.18347448383978729 
		78 0.13147174017834276
		4 63 0.38281834125518799 70 0.32671090960502625 71 0.15494011342525482 
		78 0.13553063571453094
		4 63 0.31578546762466431 70 0.23939879238605499 71 0.25076675415039062 
		78 0.19404898583889008
		4 63 0.3338674008846283 70 0.21074235439300537 71 0.28181886672973633 
		78 0.17357137799263
		4 63 0.25688564777374268 70 0.16223391890525818 71 0.34612038731575012 
		78 0.23476004600524902
		4 63 0.2856488823890686 70 0.15614557266235352 71 0.35347524285316467 
		78 0.20473030209541321
		4 63 0.20621042107202425 70 0.11551079985134899 71 0.41390097449646124 
		78 0.26437780458016547
		4 63 0.17868314949695988 70 0.11702144320341115 71 0.40698862682265979 
		78 0.29730678047696918
		4 63 0.23999390363684153 70 0.18225376579543598 71 0.31709772820916365 
		78 0.26065460235855881
		4 63 0.16583505272865295 70 0.12843519449234009 71 0.38260471820831299 
		78 0.32312503457069397
		4 63 0.10756084322929382 70 0.074052035808563232 71 0.46692606806755066 
		78 0.35146105289459229
		4 63 0.12945754536708715 70 0.076569771545310958 71 0.47264819280844494 
		78 0.32132449027915694
		4 63 0.067795836445627158 70 0.042374306058500795 71 0.52487982101559372 
		78 0.36495003648027829
		4 63 0.053849090693132443 70 0.038788434696025172 71 0.51660943801119086 
		78 0.39075303659965155
		4 63 0.10046540125857739 70 0.079484246078996013 71 0.44524299766687303 
		78 0.37480735499555351
		4 63 0.049546043212427726 71 0.4874036799206507 77 0.055374989910982775 
		78 0.4076752869559388
		4 63 0.021393148188678272 71 0.53543907304212623 77 0.03337148198229916 
		78 0.40979629678689633
		2 63 0.028595406135985164 71 0.55429922708423096;
	setAttr ".wl[560:698].w"
		2 77 0.027100022478401327 78 0.39000534430138256
		4 63 0.009994659721771772 71 0.55974669098476604 77 0.024139773460325205 
		78 0.40611887583313699
		4 63 0.0072175173294968739 71 0.53772793272274977 77 0.030228121984952411 
		78 0.42482642796280096
		4 63 0.019409476028843558 71 0.50518042319622281 77 0.05017166631456154 
		78 0.42523843446037207
		4 63 0.0063782711246030219 71 0.51114672208189948 77 0.046677347077012002 
		78 0.43579765971648554
		4 63 0.0024414435893063027 71 0.533119697364558 77 0.028412300236213401 
		78 0.4360265588099223
		4 63 0.0033722439161157579 71 0.55211718162978096 77 0.022430763165616791 
		78 0.42207981128848654
		4 63 0.001388571001651827 71 0.54787516963863281 77 0.021576257568251218 
		78 0.42916000179146419
		4 63 0.0010070954238440403 71 0.53713284797455274 77 0.027664606811056237 
		78 0.43419544979054703
		4 63 0.0020141908429984275 71 0.51410697693687457 77 0.04444952950697556 
		78 0.4394293027131515
		3 71 0.52306402119296802 77 0.044327460559662135 78 0.43260851824736979
		3 71 0.55945676565170288 77 0.027374684810638428 78 0.41316854953765869
		3 71 0.54297703909111794 77 0.044480048451424004 78 0.412542912457458
		3 71 0.59212635844710548 77 0.024704355286353168 78 0.38316928626654134
		3 71 0.57062637805938721 77 0.039002060890197754 78 0.39037156105041504
		3 71 0.62137789228608342 77 0.018738080025517346 78 0.35988402768839928
		3 71 0.62862593286834245 77 0.015259021978410083 78 0.35611504515324743
		3 71 0.64377813572022113 77 0.012710764814752865 78 0.34351109946502595
		3 71 0.59697871510716205 77 0.028259709056322142 78 0.37476157583651576
		3 71 0.6157778340934037 77 0.01924162680398156 78 0.36498053910261474
		3 71 0.64924084958832473 77 0.011886778254378276 78 0.33887237215729699
		3 71 0.65404744174419793 77 0.010482948468680465 78 0.33546960978712159
		3 71 0.67132066930099576 77 0.0085145345868781076 78 0.32016479611212617
		3 71 0.66269933436774464 77 0.012451361725650411 78 0.32484930390660499
		3 71 0.63193713323900758 77 0.020920117888373703 78 0.3471427488726187
		3 71 0.6350499892972411 77 0.024399175876391295 78 0.34055083482636755
		3 71 0.61637293833216322 77 0.041397727717476129 78 0.34222933395036059
		3 71 0.61242085695266724 77 0.044892042875289917 78 0.34268710017204285
		3 71 0.61211566292894892 77 0.066208897047969784 78 0.32167544002308129
		3 71 0.60289921173152961 77 0.072449835313851699 78 0.32465095295461871
		3 71 0.60090028791948935 77 0.11783016385264572 78 0.28126954822786487
		3 71 0.62026397987610149 77 0.10087739450758559 78 0.27885862561631297
		3 71 0.62168306575479404 77 0.071778439520138793 78 0.30653849472506711
		3 71 0.64432745691889926 77 0.11963073075092784 78 0.23604181233017285
		3 71 0.62233919832615847 77 0.15437552562915571 78 0.22328527604468579
		3 71 0.64347295994351872 77 0.17221331339756676 78 0.18431372665891457
		3 71 0.64121461870096053 77 0.098680095354916092 78 0.26010528594412335
		3 71 0.6572671034524904 77 0.16212710979770287 78 0.18060578674980679
		3 71 0.64475471261705986 77 0.23567559000608018 78 0.11956969737685991
		3 71 0.64690623739641195 77 0.23006027251302383 78 0.12303349009056419
		3 71 0.61225300571133934 77 0.3247272348051724 78 0.063019759483488202
		3 71 0.60952163196743747 77 0.32074463606435533 78 0.069733731968207147
		3 71 0.56937514675082368 77 0.4059204979628232 78 0.024704355286353168
		3 71 0.58132295717815019 77 0.37851529608452139 78 0.040161746737328419
		3 71 0.56821543930832097 77 0.4152895579815023 78 0.016495002710176676
		3 71 0.59417105053088282 77 0.38667887665338185 78 0.019150072815735299
		3 71 0.64144350173509035 77 0.35184252851937481 78 0.0067139697455348962
		3 71 0.60955214954578985 77 0.36556038532823609 78 0.024887465125974007
		4 1 0.0010681315459495186 71 0.62919051246165481 77 0.35994506334816884 
		78 0.0097962926442268783
		4 1 0.0016327153482685634 71 0.68014037846636621 77 0.31424430122451497 
		78 0.0039826049608502247
		4 1 0.0028839551895075825 71 0.66158540242865593 77 0.32983902688082428 
		78 0.0056916155010122791
		4 1 0.0035553520737852391 71 0.72703134454972251 77 0.26660564336972631 
		78 0.0028076600067660257
		4 1 0.0023498893600544715 71 0.77277791122246164 77 0.22299533973380409 
		78 0.0018768596836798699
		4 1 0.0061951627977436278 71 0.83100633594361151 77 0.16119630398336632 
		78 0.0016021972752785245
		3 1 0.0028839551613057102 71 0.87948424340736786 77 0.11763180143132644
		3 1 0.014862288177147572 71 0.90817120059280998 77 0.0769665112300425
		3 1 0.0061493860271322259 71 0.93325703901584711 77 0.060593574957020696
		3 1 0.014114595268086819 71 0.95815976169429307 77 0.027725643037620203
		3 1 0.0060578318482444344 71 0.97190813988376423 77 0.022034028267991373
		3 1 0.013122758510343989 71 0.97497520470120458 77 0.011902036788451526
		3 1 0.0028992141178456892 71 0.97567711852211947 77 0.021423667360034915
		3 1 0.0055085071593413892 71 0.98467994148941684 77 0.0098115513512417492
		3 1 0.031280994094823544 71 0.96026550739731587 77 0.0084534985078605976
		3 1 0.02981612881337322 71 0.95423819234248941 77 0.01594567884413732
		3 1 0.054230563696114294 71 0.93401998890390614 77 0.01174944739997958
		4 1 0.064209966924735823 63 0.0011902036904840197 71 0.91334401242730001 
		77 0.021255816957480123
		3 1 0.033539328599202153 71 0.92932021271690646 77 0.037140458683891375
		4 1 0.072571912759528137 63 0.0029755093446770958 71 0.87685968717041096 
		77 0.047592890725383787
		4 1 0.035553522076890595 63 0.0025635156541735341 71 0.8705577173218344 
		77 0.091325244947101508
		4 1 0.016784925498378175 71 0.81025406077306339 77 0.17021438970849484 
		78 0.0027466240200636391
		4 1 0.039612418833412093 63 0.008117799427904018 71 0.77178607286718104 
		77 0.18048370887150283
		4 1 0.021942473743646652 63 0.0079346913105371279 71 0.69895475451876643 
		77 0.27116808042704982
		4 1 0.046997788418125575 63 0.024460210940610412 71 0.6583505150237956 
		77 0.27019148561746842
		4 1 0.081605248913217798 63 0.024338139447738785 71 0.71134508318589151 
		77 0.18271152845315197
		4 1 0.076935990283467051 63 0.0084687572336696205 71 0.81136797422916485 
		77 0.10322727825369846
		4 1 0.14608988057009964 63 0.02441443484712813 71 0.72268253026394147 
		77 0.10681315431883071
		4 1 0.1457236579913446 63 0.059494928412063844 71 0.62561989762812698 
		77 0.16916151596846454
		4 1 0.086533913460386844 63 0.060593576593553494 71 0.59844358112909457 
		77 0.25442892881696511
		4 1 0.1486228748745583 63 0.12492561712639383 71 0.51349659304310658 
		77 0.21295491495594129
		4 1 0.23659113578329538 63 0.11569390704543681 71 0.51290149643051985 
		77 0.1348134607407479
		4 1 0.23718624347119577 63 0.055710689478606495 71 0.60723276303483764 
		77 0.099870304015360123
		4 1 0.32834363228338681 63 0.095658809659323163 71 0.49240863690084691 
		77 0.083588921156443063
		4 1 0.38152132006766382 63 0.17355612178975524 71 0.3675745780404594 
		77 0.07734798010212153
		4 1 0.54354161631548725 63 0.14316015105500987 71 0.27794307780947253 
		77 0.035355154820030425
		4 1 0.51143663740577816 63 0.24637216146013019 71 0.20561532523024584 
		77 0.036575875903845756
		4 1 0.64838636042249642 63 0.18399328027664363 71 0.1501182618553159 
		77 0.017502097445544037
		4 1 0.59452200268128141 63 0.29065385623269074 69 0.0220950638247378 
		71 0.09272907726129001
		4 1 0.70565347352062369 63 0.21959258145594096 69 0.0097047377161598135 
		71 0.065049207307275606
		4 1 0.745586333575883 63 0.13498130402998634 71 0.11094834624524691 
		77 0.0084840161488838051
		4 1 0.66547645006018719 63 0.11360342203681162 71 0.20369269219385244 
		77 0.017227435709148739
		4 1 0.7293354699077208 63 0.081391623211288289 71 0.17947661458801911 
		77 0.0097962922929718099
		4 1 0.69103532128548761 63 0.052002745933794933 71 0.24759289299482434 
		77 0.0093690397858931154
		4 1 0.77746242429588441 63 0.066086821381164382 71 0.15121690957102349 
		77 0.0052338447519277125
		4 1 0.79986267462513461 63 0.10371556771837991 71 0.091844051135438906 
		77 0.0045777065210465609
		4 1 0.82328526613160347 63 0.092713816205547403 69 0.0027008468241503944 
		71 0.08130007083869871
		4 1 0.7983062408564785 63 0.064133667590599214 71 0.13432517885433362 
		77 0.0032349126985886517
		4 1 0.72600900045023853 63 0.04321354935745076 71 0.22517738900814371 
		77 0.0056000611841669498
		4 1 0.75243763223680105 63 0.043900205581164406 71 0.20006103310580561 
		77 0.0036011290762289565
		4 1 0.67280078780167796 63 0.028747998539449628 71 0.29294270645335924 
		77 0.0055085072055131639
		4 1 0.59955748280642018 63 0.033478294877417741 71 0.35611505709293523 
		77 0.010849165223226827
		4 1 0.59748226515479808 63 0.072831310467480329 71 0.30885785875629235 
		77 0.020828565621429245
		4 1 0.47273974906295912 63 0.042908369855457991 71 0.45803006800964374 
		77 0.026321813071939155
		4 1 0.4490119798145743 63 0.092988475810779347 71 0.40993362512464215 
		77 0.048065919250004294
		4 1 0.35043869466896937 63 0.050888837900425136 71 0.5439536137567047 
		77 0.054718853673900773
		4 1 0.34088655798306228 63 0.021011672600929846 71 0.60932325408871102 
		77 0.028778515327296923
		4 1 0.44663157393587272 63 0.017135880632163873 71 0.5230792682904114 
		77 0.013153277141552015
		4 1 0.29633020236960317 63 0.007476920445621686 71 0.68169680646739839 
		77 0.014496070717376783
		4 1 0.39884031413257592 63 0.0074616620497653195 71 0.58652628342101398 
		77 0.0071717403966447772
		4 1 0.23985656375496259 63 0.0031280993941415051 71 0.74843976633885645 
		77 0.0085755705120394484
		4 1 0.31316090811324937 63 0.0039673458418599391 71 0.67760738306036139 
		77 0.0052643629845294179
		4 1 0.18477149019490699 63 0.0019378957501987426 71 0.80737011365271238 
		77 0.0059205004021819852
		4 1 0.20384527695401275 63 0.0025635156720794838 71 0.78918134982422616 
		77 0.0044098575496816601
		4 1 0.13896390779530174 63 0.0017242694719179191 71 0.85511559148422034 
		77 0.0041962312485600926
		4 1 0.1871671673149482 63 0.0031738765478620742 71 0.80491340010443069 
		77 0.0047455560327590331
		4 1 0.13430991549936727 63 0.0023804073765341851 71 0.85877774746286628 
		77 0.0045319296612322622
		4 1 0.17717249839990631 63 0.00448615247418673 71 0.81263447489003682 
		77 0.0057068742358701938
		4 1 0.091386281485822299 63 0.0017853055718896537 71 0.90264744091923033 
		77 0.0041809720230578211
		3 1 0.057694362239217811 71 0.93926909231849953 77 0.0030365454422826873
		3 1 0.036835279032689468 71 0.96046387411297585 77 0.0027008468543347096
		4 1 0.064759291633079655 63 0.0013885709906595631 71 0.92980849634645457 
		77 0.0040436410298062943
		3 1 0.027496757408321366 71 0.96972610056445063 77 0.0027771420272279935
		4 1 0.053345542227188687 63 0.0011291676164119629 71 0.94132905891663232 
		77 0.0041962312397669918
		4 1 0.10466162909130393 63 0.0027161059096274241 71 0.88685435469660145 
		77 0.0057679103024672268
		4 1 0.13150225509317781 63 0.0034943159948174684 71 0.85935759084177565 
		77 0.0056458380702290971
		4 1 0.16809338104226251 63 0.0054169529317451481 71 0.81931792583306329 
		77 0.0071717401929290662
		4 1 0.14705120218798223 63 0.0043183034848945671 71 0.84112305545781074 
		77 0.0075074388693125394
		4 1 0.18483252857780555 63 0.0062867170316851084 71 0.80067140013104565 
		77 0.008209354259463687
		4 1 0.21557946131730449 63 0.0080415046319665048 71 0.76867322789462778 
		77 0.0077058061561012508
		4 1 0.20807202402586145 63 0.0069733733191780431 71 0.77807278346820719 
		77 0.0068818191867533515
		4 1 0.26321812790027027 63 0.0086976427219946171 71 0.72146181404571996 
		77 0.0066224153320152109
		4 1 0.23466849436363435 63 0.0057068742146104308 71 0.75391775720714482 
		77 0.0057068742146104308
		4 1 0.28992139915106857 63 0.0072175174941818739 71 0.69753568455064707 
		77 0.0053253988041024811
		4 1 0.24362554370817227 63 0.0042877855105933208 71 0.74757000016835984 
		77 0.0045166706128745562
		4 1 0.31534293103057048 63 0.0061951628511133063 71 0.67450981923908571 
		77 0.0039520868792305101
		4 1 0.2971694444543449 63 0.0042114900072073467 71 0.69448387040723603 
		77 0.0041351951312117684
		4 1 0.41817349565462042 63 0.0075837341808206163 71 0.57070267705402844 
		77 0.0035400931105305298
		4 1 0.43898679559203119 63 0.0072480354261909791 71 0.54941634763293101 
		77 0.0043488213488468421
		4 1 0.55815976468268946 63 0.01377889690609488 71 0.42383458914350775 
		77 0.0042267492677079332
		3 1 0.56220340571681959 63 0.017074845683551824 71 0.41419088724761022;
	setAttr ".wl[698:828].w"
		1 77 0.006530861352018468
		4 1 0.67818723735346231 63 0.02668802944900036 71 0.29123368269360383 
		77 0.0038910505039334779
		4 1 0.55233080815376756 63 0.014526589268434385 71 0.430060280064958 
		77 0.0030823225128400692
		4 1 0.67298388904206574 63 0.027924010705656439 71 0.29620814509634391 
		77 0.0028839551559339252
		4 1 0.75382620640299569 63 0.047714960174440352 71 0.19575798652798346 
		77 0.0027008468945804642
		4 1 0.74116121480157426 63 0.052506293221271337 71 0.20401312068827807 
		77 0.0023193712888763445
		4 1 0.65685512027093584 63 0.031250477499280463 71 0.30937666356407023 
		77 0.0025177386657135137
		4 1 0.53955901648979709 63 0.017441062573437319 71 0.44016174281309728 
		77 0.0028381781236682772
		4 1 0.54164950791203847 63 0.021835660058602144 71 0.43341725065645115 
		77 0.0030975813729081873
		4 1 0.41676965559650275 63 0.010009918410845168 71 0.56987870018171449 
		77 0.0033417258109376398
		4 1 0.43303577912384966 63 0.013687342032459793 71 0.54953841858171049 
		77 0.0037384602619801063
		4 1 0.45287250312604582 63 0.016876477315925877 71 0.52588693940835929 
		77 0.00436408014966901
		4 1 0.37619593371631826 63 0.012893873140788015 71 0.60558479432143242 
		77 0.0053253988214613055
		4 1 0.37752345749327315 63 0.014602883929707763 71 0.60193789874206993 
		77 0.0059357598349491858
		4 1 0.32021057844318879 63 0.012314030992344252 71 0.66076142088146084 
		77 0.0067139696830061796
		4 1 0.3198596185469319 63 0.010574501761849009 71 0.66341649373853873 
		77 0.0061493859526804209
		4 1 0.34842450286564353 63 0.009445335017797889 71 0.63758297348017701 
		77 0.0045471886363816433
		4 1 0.2641184036882937 63 0.010162509065424109 71 0.71845579281161687 
		77 0.0072632944346653194
		4 1 0.44910353798599156 63 0.017898833529175727 71 0.52805370535001472 
		77 0.0049439231348180285
		4 1 0.55373465189733129 63 0.024826427551710196 71 0.41789882752450069 
		77 0.003540093026457831
		4 1 0.54502176350179987 63 0.02441443463111985 71 0.42658119698504832 
		77 0.0039826048820320653
		4 1 0.64881361739362808 63 0.03892576394464381 71 0.30933088640367401 
		77 0.0029297322580540972
		4 1 0.64608224698142291 63 0.035934997223644648 71 0.31534294490723408 
		77 0.0026398108876983578
		4 1 0.7256885699398018 63 0.056824597932169235 71 0.21516746082187202 
		77 0.0023193713061570066
		4 1 0.77741665209175925 63 0.081559472374698058 71 0.13905546169511959 
		77 0.0019684138384230502
		4 1 0.76995498390143613 63 0.081376366790944982 71 0.14660868134005392 
		77 0.002059967967564985
		4 1 0.71897458979931572 63 0.058991379994672223 71 0.21954680963916695 
		77 0.0024872205668451121
		4 1 0.71137559678917983 63 0.055573359338839945 71 0.23036545600878244 
		77 0.0026855878631978775
		4 1 0.64095521868609662 63 0.03680476225174166 71 0.31900510637562407 
		77 0.0032349126865376626
		4 1 0.76078431912716116 63 0.076737619043122748 71 0.16025024465925242 
		77 0.0022278171704637681
		4 1 0.80396734825835314 63 0.10553139337596654 69 0.001663233368926332 
		71 0.088838024996753986
		4 1 0.80050354916426492 63 0.096513315698201832 71 0.10128938371330948 
		77 0.0016937514242235871
		4 1 0.79897764924235204 63 0.15222399973201753 69 0.0017090104010996103 
		71 0.047089340624530893
		4 1 0.78988326515400853 63 0.15910582429619768 69 0.0016784924277860255 
		71 0.049332418122007719
		4 1 0.74137483594610554 63 0.23299000707031914 69 0.0019989318293725743 
		71 0.023636225154202738
		4 1 0.79630731646373143 63 0.17073319661542927 69 0.0018310826067132956 
		71 0.031128404314126026
		4 1 0.72452887510355723 63 0.25438315588398974 69 0.0022888533660404891 
		71 0.01879911564641255
		4 1 0.64159608380232724 63 0.34131381177887221 69 0.0025482566757342941 
		71 0.014541847743066254
		4 1 0.73047989164654226 63 0.24075685295749499 69 0.001861600659694146 
		71 0.026901654736268561
		4 1 0.62568093016308801 63 0.35745785023157045 69 0.0022278172202593628 
		71 0.014633402385082215
		4 1 0.73080033285087076 63 0.24104677213672734 69 0.0018768596985375453 
		71 0.026276035313864344
		4 1 0.79925230650683943 63 0.15187304741723573 69 0.0017853055062131882 
		71 0.047089340569711688
		4 1 0.81307697864070294 63 0.13963531055232958 69 0.002227817211960097 
		71 0.045059893595007436
		4 1 0.80994887743976574 63 0.10601968525574858 69 0.0016479743966902256 
		71 0.082383462907795538
		4 1 0.80238039889427226 63 0.11076524327859415 69 0.0016327153748787956 
		71 0.085221642452254803
		4 1 0.78876936362239591 63 0.077195390987028004 71 0.13202105450255699 
		77 0.0020141908880191009
		4 1 0.79914549721949613 63 0.06977950584997418 71 0.12874036664665109 
		77 0.0023346302838785889
		4 1 0.82194246717924702 63 0.0970016069265911 69 0.0019378958241957926 
		71 0.07911803006996608
		4 1 0.81582360680942245 63 0.1318379478982287 69 0.0030670633712435147 
		71 0.049271381921105396
		4 1 0.74822614416944755 63 0.22447546668468094 69 0.0022583351749848662 
		71 0.025040053970886701
		4 1 0.76923781275172809 63 0.1991912713312019 69 0.0031128404517060124 
		71 0.028458075465364031
		4 1 0.77781337535838291 63 0.16658274837144779 69 0.0048523689642792425 
		71 0.050751507305890092
		4 1 0.70373083504520551 63 0.2642862549218053 69 0.0054474711526866617 
		71 0.026535438880302475
		4 1 0.61721217919705529 63 0.33624780334647653 69 0.011627375202380937 
		71 0.034912642254087342
		4 1 0.57901884689139815 63 0.40126649629019984 69 0.0065918976358743681 
		71 0.013122759182527676
		4 1 0.66576637186149001 63 0.31602961465124424 69 0.0035553521731206306 
		71 0.014648661314145087
		4 1 0.51602959969286544 63 0.47269398282175684 69 0.0043640802898896507 
		71 0.0069123371954880287
		4 1 0.48180363087010647 63 0.50913250979757008 69 0.0030365453885506238 
		71 0.0060273139437728397
		4 1 0.34349585275262112 63 0.65001906281142929 69 0.0033112078178848792 
		71 0.003173876618064769
		4 1 0.37163347126982843 63 0.62078279459172847 69 0.0031738765641195401 
		71 0.0044098575743236595
		4 1 0.4820325079947006 63 0.5082474950525776 69 0.0025787747017425307 
		71 0.0071412222509793163
		4 1 0.6317082489073822 63 0.35303272933968421 69 0.0025787746368974127 
		71 0.012680247116036259
		4 1 0.61762416233340811 63 0.36662852687303521 69 0.0021515220824247926 
		71 0.013595788711131993
		4 1 0.49855801405087347 63 0.48963150325041321 69 0.002944991221948304 
		71 0.0088654914767650281
		4 1 0.39807735789216803 63 0.59232471759850347 69 0.0036469061331152876 
		71 0.0059510183762132305
		4 1 0.44817272684307852 63 0.53942168788811629 69 0.0039215689342395992 
		71 0.008484016334565669
		4 1 0.54518961309829916 63 0.44042112941392858 69 0.0032806896711251666 
		71 0.011108567816647076
		4 1 0.49953460042040387 63 0.48595406971559207 69 0.0039520868516255024 
		71 0.010559243012378549
		4 1 0.38986801465722709 63 0.59734492520472393 69 0.0048371100941212598 
		71 0.0079499500439277615
		4 1 0.37524986756359985 63 0.61390096749608747 69 0.0044403756616313564 
		71 0.0064087892786814362
		4 1 0.30092316907959504 63 0.68746471501067008 69 0.0053559169248061957 
		71 0.0062561989849287073
		4 1 0.31136032677978004 63 0.67833983329584957 69 0.0048676281759434809 
		71 0.0054322117484268675
		4 1 0.32228580882613372 63 0.66953535477924309 69 0.0040131230860339841 
		71 0.0041657133085892433
		4 1 0.26277562914701263 63 0.73121231624108662 69 0.0035400930709669062 
		71 0.0024719615409337882
		4 1 0.23590448015378923 63 0.75690852044896473 69 0.0041351950811461622 
		71 0.0030518043161000172
		4 1 0.16467536468264315 63 0.8303349353151358 69 0.003418020796628481 
		71 0.0015716792055925604
		4 1 0.21857022684436414 63 0.77586023030598539 69 0.0038910504840024506 
		71 0.0016784923656481159
		3 1 0.11612116043709787 63 0.88036926445393682 69 0.0035095751089653372
		4 1 0.18142977010522943 63 0.81145952582832404 69 0.0057068740790794433 
		71 0.0014038299873671356
		4 1 0.33635461173786496 63 0.65552758865278404 69 0.0050659952449333143 
		71 0.0030518043644176592
		4 1 0.26047149882774423 63 0.72735180096369534 69 0.0093080040285290194 
		71 0.0028686961800313631
		4 1 0.1355001146029651 63 0.85398641981964962 69 0.0092317077717857278 
		71 0.0012817578055996275
		4 1 0.18611429900375348 63 0.79436941101469627 69 0.016433967514640182 
		71 0.0030823224669098838
		4 1 0.3279621604159122 63 0.64864575923294365 69 0.0157778281865435 
		71 0.0076142521646006519
		4 1 0.22067597713951001 63 0.73882657977590882 69 0.031601433005197278 
		71 0.0088960100793839432
		4 1 0.36443123153516793 63 0.58271151672543675 69 0.03006027260784009 
		71 0.022796979131555224
		4 1 0.48482489766487813 63 0.48413825215450768 69 0.013809414631908441 
		71 0.01722743554870574
		4 1 0.49874112195797682 63 0.42519265571680909 69 0.026657510648136998 
		71 0.049408711677077083
		4 1 0.45297932962312804 63 0.37779811306147359 69 0.047394521887559604 
		71 0.12182803542783882
		4 1 0.35483330091647841 63 0.52736704952232094 69 0.056107423572531824 
		71 0.061692225988668657
		4 1 0.31358816752451407 63 0.4563515714354579 69 0.090043483822889861 
		71 0.14001677721713815
		4 1 0.36986341796917166 63 0.31180286175159466 69 0.069748989718042387 
		71 0.24858473056119135
		4 1 0.25230792164802551 63 0.35898375511169434 69 0.12297245860099792 
		71 0.26573586463928223
		4 1 0.25152972715392302 63 0.21528953634633924 71 0.39308766116332505 
		77 0.14009307533641271
		4 1 0.16401922947197003 63 0.23041123495118671 71 0.39349964847415164 
		77 0.21206988710269165
		4 1 0.094514386274134915 63 0.12707713435705206 71 0.4924849345160266 
		77 0.28592354485278643
		4 63 0.2213016003370285 69 0.15768672525882721 71 0.36696422100067139 
		77 0.2540474534034729
		4 63 0.12347600517067309 69 0.1016556016977459 71 0.46236362708834089 
		77 0.31250476604324007
		4 1 0.054657817701366809 63 0.061509118400650001 71 0.5629358375509953 
		77 0.32089722634698786
		4 1 0.02922102562816575 63 0.024887464430626279 71 0.611688422544724 
		77 0.33420308739648397
		4 63 0.062027924456014384 69 0.052445259531348119 71 0.54027617581497334 
		77 0.34525064019766422
		4 63 0.025497826338701117 71 0.58670939217098672 77 0.35802242893399061 
		78 0.029770352556321544
		4 1 0.013092241371909542 71 0.63746089336891565 77 0.33582055881452338 
		78 0.013626306444651508
		4 1 0.0082246133243062593 71 0.71258106369346419 77 0.27412832753441896 
		78 0.0050659954478105779
		4 1 0.0050659952354971628 71 0.64025330126120428 77 0.343694207811859 
		78 0.01098649569143963
		4 1 0.0018005645406298379 71 0.62746624648534766 77 0.35732050881565269 
		78 0.013412680158369853
		4 1 0.0030518043558910163 71 0.61673914926693474 77 0.35735103221721176 
		78 0.022858014159962428
		4 63 0.0080567633494833726 71 0.60808728539716084 77 0.35893796938446987 
		78 0.024917981868885931
		4 63 0.0079804687795658538 71 0.59917599688217793 77 0.34888229196469278 
		78 0.04396124237356349
		4 63 0.0019378957953188943 71 0.61377889389514539 77 0.3416952815083657 
		78 0.042587928801170002
		4 1 0.0011444266390547406 71 0.61695277532877368 77 0.35164415746273342 
		78 0.030258640569437983
		3 71 0.62471960811466709 77 0.31949340702046813 78 0.055786984864864782
		3 71 0.6139009732134858 77 0.33296710997001328 78 0.053131916816500951
		3 71 0.62949568502229214 77 0.27917906849964758 78 0.091325246478060229
		3 71 0.59710078986659054 77 0.35367360447590346 78 0.049225605657505944
		3 71 0.61698329908388327 77 0.28804454422030257 78 0.094972156695814103
		3 71 0.6129091336361383 77 0.29849698917197443 78 0.088593877191887216
		3 71 0.62757306355874143 77 0.21698328529323213 78 0.15544365114802641
		3 71 0.62334631015818387 77 0.2241397731262513 78 0.15251391671556483
		3 71 0.61501486025772778 77 0.15300221969190567 78 0.23198292005036653
		3 71 0.63265430927276611 77 0.14045929908752441 78 0.22688639163970947
		3 71 0.60495918087722089 77 0.086991681352381681 78 0.30804913777039739
		3 71 0.62355993319869241 77 0.086137172992909766 78 0.29030289380839785
		3 71 0.59601741141054909 77 0.049851223083567278 78 0.35413136550588359
		3 71 0.6126649861658926 77 0.06172274310658233 78 0.32561227072752508
		3 71 0.59249257489580121 77 0.029938200209865345 78 0.37756922489433342
		3 71 0.58878462300332102 77 0.030624856544894313 78 0.38059052045178465
		3 71 0.61646449451061991 77 0.019592585005624993 78 0.36394292048375509
		3 71 0.60688181313936673 77 0.037293051410657765 78 0.35582513544997552
		3 71 0.57355611875404289 77 0.043610285480205506 78 0.38283359576575166
		3 71 0.56876479731850627 77 0.067597462719716686 78 0.36363773996177701;
	setAttr ".wl[829:963].w"
		3 71 0.55027085542678833 77 0.093812465667724609 78 0.35591667890548706
		3 71 0.5736629281392257 77 0.13165484172620115 78 0.29468223013457312
		3 71 0.53134966292492791 77 0.11656367120566719 78 0.35208666586940485
		3 71 0.56359195709228516 77 0.15982300043106079 78 0.27658504247665405
		3 71 0.60538643598556519 77 0.17399862408638 78 0.22061493992805481
		3 71 0.58782328926990302 77 0.10370031308234672 78 0.30847639764775031
		3 71 0.60550850629806519 77 0.19638361036777496 78 0.19810788333415985
		3 71 0.63106738580662924 77 0.23184556913605975 78 0.13708704505731098
		3 71 0.63932250977572036 77 0.2393682712410648 78 0.12130921898321481
		3 71 0.64066528319321148 77 0.27447929569364643 78 0.084855421113142052
		4 63 0.0017242694927939834 71 0.64083314643221856 77 0.27388418020507238 
		78 0.083558403869915046
		4 63 0.001449607134188234 71 0.62684061492824439 77 0.30925459828926027 
		78 0.062455179648307137
		4 63 0.0052185854607241042 71 0.63179981384901429 77 0.27011519532126044 
		78 0.092866405369001231
		4 63 0.0064850846672703704 71 0.61356527841803943 77 0.31136033562407567 
		78 0.06858930129061451
		4 63 0.020096132045146604 71 0.59659723983003921 77 0.27489128043207034 
		78 0.10841534769274384
		4 63 0.025040055020303251 71 0.5794918612697032 77 0.31992066323653728 
		78 0.075547420473456278
		4 63 0.026016632337278058 71 0.5743495875443293 77 0.35016402928311408 
		78 0.049469750835278548
		4 63 0.065720610810224789 71 0.53580528896901969 77 0.31650263306873017 
		78 0.081971467152025301
		4 63 0.060852980872179531 71 0.54467078295118598 77 0.27815670914845092 
		78 0.11631952702818363
		4 63 0.13150225579738617 71 0.48276492953300476 77 0.269306480884552 
		78 0.11642633378505707
		4 63 0.14116121933729364 69 0.10402075278774464 71 0.45952543958667991 
		77 0.29529258828828175
		4 63 0.065171281198194361 71 0.53691919458014059 77 0.34387732705062607 
		78 0.054032197171039041
		4 63 0.12538337894355325 69 0.10263218138563904 71 0.45725185360389731 
		77 0.3147325860669104
		4 63 0.21315326969097154 69 0.16878004120618043 71 0.35326161454228139 
		77 0.26480507456056662
		4 63 0.21618981659412384 69 0.16868849098682404 71 0.35538262128829956 
		77 0.25973907113075256
		4 63 0.32442206144332886 69 0.24007019400596619 71 0.24158082902431488 
		77 0.19392691552639008
		4 63 0.33966583013534546 69 0.22706951200962067 71 0.24452582001686096 
		77 0.18873883783817291
		4 1 0.17146563274464557 63 0.37265583317494638 69 0.19005112066788793 
		71 0.26582741341252009
		4 1 0.14081024913772569 63 0.4838178085711925 69 0.23202868950324224 
		71 0.14334325278783958
		4 1 0.2074006199836731 63 0.49338522553443909 69 0.15420767664909363 
		71 0.14500647783279419
		4 1 0.14279392148861406 63 0.60750745821733099 69 0.18113983897656441 
		71 0.068558781317490616
		4 1 0.22612344713233157 63 0.60053406803606302 69 0.10560768606645571 
		71 0.067734798765149734
		4 1 0.13226519401869555 63 0.72191958947182089 69 0.11841001251330588 
		71 0.027405203996177727
		4 1 0.23192187042403375 63 0.68015564628206349 69 0.061631188829766023 
		71 0.026291294464136753
		4 1 0.12193484615714741 63 0.80473029688441222 69 0.064133666515474835 
		71 0.0092011904429655442
		4 1 0.11030747140227314 63 0.85638208313784492 69 0.030258641041462284 
		71 0.0030518044184197316
		4 1 0.052826731363906192 63 0.88128481571843742 69 0.063141829030608373 
		71 0.0027466238870480081
		4 1 0.061692226161034744 63 0.80045776888344444 69 0.12875562798343537 
		71 0.0090943769720854307
		4 1 0.02401770048928898 63 0.83852903512183929 69 0.13492026680061109 
		71 0.0025329975882606086
		3 1 0.019974060877481201 63 0.91973754181773515 69 0.060288397304783692
		3 1 0.046616313245169953 63 0.92739757160873793 69 0.025986115146092132
		3 1 0.01744106215923431 63 0.96058594643742246 69 0.021972991403343203
		3 1 0.035492483691743036 63 0.95335317101959682 69 0.011154345288660123
		4 1 0.088319221437855686 63 0.89590294983786456 69 0.014602884014707737 
		71 0.0011749447095720539
		3 1 0.058915082475012322 63 0.93363851482726357 69 0.0074464026977241089
		3 1 0.02220187708735466 63 0.97267109155654907 69 0.0051270313560962677
		3 1 0.036301213681655627 63 0.95999084405615309 69 0.0037079422621912948
		3 1 0.084824904759961697 63 0.91026169019273406 69 0.0049134050473042742
		3 1 0.050156401943272949 63 0.94729534147117622 69 0.0025482565855508357
		3 1 0.029602503383344154 63 0.96876478127522991 69 0.0016327153414259325
		3 1 0.082658120519686587 63 0.91473258670438717 69 0.0026092927759263007
		3 1 0.045273516147944663 63 0.95275807003563107 69 0.0019684138164243114
		3 1 0.018371863217949477 63 0.9802700838389361 69 0.0013580529431144474
		3 1 0.008712901930592834 63 0.98977645486786869 69 0.0015106432015384525
		3 1 0.01638818926506834 63 0.9813076983984883 69 0.0023041123364433654
		3 1 0.0043488214318750289 63 0.99159227878235023 69 0.0040588997857747616
		3 1 0.0024567025962955839 63 0.99409475835548822 69 0.0034485390482161616
		3 1 0.0018158235600467024 63 0.98666361496480959 69 0.011520561475143749
		3 1 0.002761883005743418 63 0.98541237460976217 69 0.011825742384494454
		3 1 0.0013733120081133249 63 0.96658274206723171 69 0.032043945924654982
		3 1 0.0021362630829460617 63 0.96530098532113151 69 0.032562751595922527
		3 1 0.0034180209486300993 63 0.96960402799253953 69 0.026977951058830427
		3 1 0.0016327153018907323 63 0.91641107898764651 69 0.081956205710462762
		3 1 0.0023956664567460133 63 0.91873044524238578 69 0.078873888300868236
		3 1 0.0036011290762289565 63 0.92809948971617384 69 0.068299381207597168
		4 1 0.0023346303539995669 63 0.83254748737914019 69 0.16366827518431148 
		70 0.0014496070825487507
		4 1 0.0037689784462179641 63 0.84483099849255849 69 0.14998093401062329 
		70 0.0014190890506002862
		4 1 0.0024719615317250138 63 0.73052566801345276 69 0.26321813304823088 
		70 0.0037842374065913788
		4 1 0.0050965132909507396 63 0.74184786962502136 69 0.24908827140843753 
		70 0.0039673456755903967
		4 1 0.0087586788182004178 63 0.84971390077379538 69 0.13992522314839334 
		70 0.0016021972596108186
		4 1 0.013397421956103828 63 0.74377049504878534 69 0.23805600881409289 
		70 0.00477607418101802
		4 1 0.0087586793259833533 63 0.65798427880502686 69 0.32277409324410128 
		70 0.010482948624888576
		4 1 0.023407340551138699 63 0.64957655867585995 69 0.31476310569751209 
		70 0.012252995075489289
		4 1 0.035431448073235311 63 0.72948806866501215 69 0.22597084750073251 
		71 0.0091096357610200331
		4 1 0.053223468858967247 63 0.62125582081504005 69 0.29733729639404727 
		71 0.02818341393194547
		4 1 0.036270696467138659 63 0.58237582119716802 69 0.35095751089440186 
		71 0.030395971441291431
		4 1 0.066147855428638228 63 0.53452353873068792 69 0.32776379096860003 
		71 0.071564814872073904
		4 63 0.51624321937561035 69 0.34129855036735535 71 0.077729456126689911 
		77 0.064728774130344391
		4 63 0.43289846181869507 69 0.29979398846626282 71 0.14628824591636658 
		77 0.12101930379867554
		4 63 0.42781720202888851 69 0.29175249176848667 71 0.15910582481482363 
		77 0.12132448138780119
		4 63 0.32414740324020386 69 0.23637750744819641 71 0.24979019165039062 
		77 0.18968489766120911
		4 63 0.32840466988689704 69 0.22171359094550597 71 0.26790264648054013 
		77 0.18197909268705684
		4 63 0.23593500256538391 69 0.17055009305477142 71 0.35245287418365479 
		77 0.24106203019618988
		4 63 0.22708477079868317 69 0.14903487265110016 71 0.38738077878952026 
		77 0.23649957776069641
		4 63 0.11886777817359401 71 0.47890439986366329 77 0.23709468720178817 
		78 0.16513313476095448
		4 63 0.22632181307193916 71 0.4054779945987762 77 0.22284274961288647 
		78 0.14535744271639819
		4 63 0.33371480802126513 69 0.20375372165808497 71 0.28697642256354655 
		77 0.17555504775710332
		4 63 0.33699550722546118 69 0.1900358618790528 71 0.30113678721879739 
		77 0.17183184367668861
		4 63 0.19383534789085388 71 0.39220264554023743 77 0.19446097314357758 
		78 0.21950103342533112
		4 63 0.089692533016204834 71 0.4609140157699585 77 0.2062561959028244 
		78 0.24313725531101227
		4 63 0.10496681261782953 71 0.41649499845873561 77 0.16574350122916326 
		78 0.31279468769427154
		4 63 0.041809719211644378 71 0.49269855205974944 77 0.20572213905201159 
		78 0.25976958967659469
		4 63 0.048493173876650142 71 0.53630883500555226 77 0.24011597484566224 
		78 0.17508201627213538
		4 63 0.017013808870816684 71 0.58254367655649475 77 0.24193179832707903 
		78 0.15851071624560947
		4 63 0.019684138326462496 71 0.53258563576039775 77 0.21306172608570362 
		78 0.23466849982743618
		4 63 0.0064850843773645011 71 0.56850539234895925 77 0.21576256517534331 
		78 0.20924695809833296
		4 63 0.0066071566356444194 71 0.51419853565517659 77 0.17192339697010586 
		78 0.3072709107390732
		4 63 0.0019226367880809186 71 0.53640038599316631 77 0.17491416901916618 
		78 0.28676280819958666
		4 63 0.0019073777379752447 71 0.59345388453927861 77 0.21666285410755978 
		78 0.18797588361518636
		3 71 0.55249864686278471 77 0.17456321678404832 78 0.27293813635316694
		3 71 0.60529488325119019 77 0.21190203726291656 78 0.18280307948589325
		4 63 0.0017547874968745368 71 0.63593500097452549 77 0.24338139304601331 
		78 0.11892881848258671
		4 63 0.006286716978990455 71 0.6161440570717599 77 0.2453803255058245 
		78 0.13218890044342513
		3 71 0.51519035525336332 77 0.12396429294400971 78 0.36084535180262695
		3 71 0.52689402510383687 77 0.074952318147535349 78 0.39815365674862779
		3 71 0.51012437015401213 77 0.076295105329301796 78 0.41358052451668609
		4 63 0.0018310825760173824 71 0.50272373940636206 77 0.12100404162879917 
		78 0.37444113638882143
		4 63 0.0018005646412442254 71 0.50107576072878557 77 0.074296178820746184 
		78 0.42282749580922407
		4 63 0.0061341269124443407 71 0.48897535496858824 77 0.11981383928691025 
		78 0.38507667883205715
		4 63 0.019119555237439769 71 0.48593881997804439 77 0.16995498632987022 
		78 0.3249866384546457
		4 63 0.018905928393650667 71 0.47112229554191659 77 0.12149233393649074 
		78 0.388479442127942
		4 63 0.0060120546119006944 71 0.49333944801860619 77 0.076066225590030137 
		78 0.42458227177946301
		4 63 0.018768597184472564 71 0.48209353742643962 77 0.079560539727353982 
		78 0.41957732566173384
		4 63 0.048859387272153887 71 0.44728770518833616 77 0.12355229911541715 
		78 0.38030060842409275
		4 63 0.048111695617021263 71 0.45555808970496769 77 0.16847486731233124 
		78 0.32785534736567978
		4 63 0.10283055079854614 71 0.41219195416426702 77 0.12420843449079666 
		78 0.36076906054639024
		4 63 0.048493171347534128 71 0.46196688652894652 77 0.084229801751419101 
		78 0.40531014037210022
		4 63 0.10116731224704814 71 0.42912947492108533 77 0.087510487623356462 
		78 0.38219272520851011
		4 63 0.1747768372297287 70 0.14146639406681061 71 0.35838863253593445 
		78 0.32536813616752625
		4 63 0.18986800312995911 71 0.36284428834915161 77 0.15475699305534363 
		78 0.29253071546554565
		4 63 0.27144274115562439 70 0.20195315778255463 71 0.28131532669067383 
		78 0.24528877437114716
		4 63 0.31479361184248905 70 0.1804989698454891 71 0.29814603480479068 
		78 0.20656138350723113
		4 63 0.38614481112145171 69 0.18092621593287264 70 0.23900206030902177 
		71 0.1939269126366539
		4 63 0.41580834984779358 69 0.21326008439064026 70 0.18242160975933075 
		71 0.18850995600223541
		4 63 0.43288319657917029 69 0.24345768625352254 70 0.13754482362352574 
		71 0.18611429354378142
		4 63 0.49408713719378616 69 0.25087356941213562 70 0.15332265426699301 
		71 0.1017166391270852
		4 63 0.50037384033203125 69 0.29051652550697327 70 0.11219958961009979 
		71 0.096910044550895691
		4 63 0.55027084517719516 69 0.29053177888445969 70 0.11415274228616167 
		71 0.04504463365218353
		4 63 0.54886703252021507 69 0.33229570714358259 70 0.078629737532108418 
		71 0.040207522804093884
		4 63 0.58144503886014698 69 0.32664987475299267 70 0.076813913953317256 
		71 0.01509117243354318
		4 63 0.58393223344389478 69 0.35695431401017047 70 0.046601054325536129 
		71 0.012512398220398612
		4 1 0.0040741589910298056 63 0.6000000109896062 69 0.34984358395784865 
		70 0.046082246061515383
		4 1 0.005859464428795369 63 0.61348897447246675 69 0.35744258894563685 
		70 0.023208972153101012
		4 1 0.0022278171787630339 63 0.61574732769853224 69 0.35835811212095997 
		70 0.023666743001744789
		4 1 0.0033417258171620891 63 0.65598535980646866 69 0.33076980933368311 
		70 0.0099031050426862319;
	setAttr ".wl[964:1113].w"
		4 1 0.0016174563696303703 63 0.64596017170111242 69 0.34233615838543058 
		70 0.010086213543826659
		4 1 0.0016021973092252212 63 0.7182421731089198 69 0.27632561506170716 
		70 0.0038300145201479101
		3 63 0.62934310299174478 69 0.36006713517122757 70 0.0105897618370277
		4 1 0.0010376135109598848 63 0.60680551636640634 69 0.36728466343837535 
		70 0.024872206684258536
		3 63 0.58609902531225777 69 0.38622110866259163 70 0.02767986602515057
		3 63 0.60817885172300468 69 0.34076446167839891 70 0.051056686598596399
		4 1 0.0016021972954227181 63 0.61004042497594757 69 0.34093233871543988 
		70 0.047425039013189882
		4 63 0.62688638823202214 69 0.29335469963719557 70 0.078477154249977699 
		71 0.0012817578808046186
		4 63 0.60813307563917174 69 0.31145188110872957 70 0.075806818655390421 
		71 0.0046082245967082811
		4 63 0.61748683165066487 69 0.26320287462695097 70 0.1141374850918656 
		71 0.0051728086305185749
		4 63 0.58927290424331669 69 0.28067445179928285 70 0.11303883559363485 
		71 0.017013808363765679
		4 63 0.5744563947887279 69 0.23700313314237284 70 0.17103837462335522 
		71 0.017502097445544037
		4 63 0.54242771661867306 69 0.24815747049392212 70 0.16220340072287842 
		71 0.047211412164526387
		4 63 0.50579078701182112 69 0.20794995826314994 70 0.23863584603265903 
		71 0.047623408692369903
		4 63 0.46831464418534452 69 0.21580834525966386 70 0.21199358841781624 
		71 0.10388342213717533
		4 63 0.43080797791481018 69 0.17695887386798859 70 0.28400090336799622 
		71 0.10823224484920502
		4 63 0.34618142247200012 70 0.27351796627044678 71 0.19906920194625854 
		78 0.18123140931129456
		4 63 0.40885022891834721 69 0.13289082248346243 70 0.33800259736184174 
		71 0.12025635123634862
		4 63 0.32033264159660574 70 0.27678340261007245 71 0.2070649235387903 
		78 0.19581903225453151
		4 63 0.24576180807110953 70 0.20595101705266511 71 0.28345158273798848 
		78 0.26483559213823687
		4 63 0.23654535765268442 70 0.19835202691483539 71 0.29480430923110706 
		78 0.27029830620137313
		4 63 0.16560616842499123 70 0.13765163514537163 71 0.36495002560391981 
		78 0.33179217082571727
		4 63 0.31178760528564453 70 0.26390478014945984 71 0.2227817177772522 
		78 0.20152589678764343
		4 63 0.39162281155586243 70 0.34444189071655273 71 0.13562218844890594 
		78 0.12831310927867889
		4 63 0.44238957103506371 70 0.39023422613390946 71 0.086579686603252784 
		78 0.080796516227774076
		4 63 0.44516670703887939 69 0.10783550888299942 70 0.38321506977081299 
		71 0.063782714307308197
		4 63 0.47441825447387354 69 0.10035859085753035 70 0.40100708753245728 
		71 0.024216067136138927
		4 63 0.48578622258566939 69 0.13333333842456332 70 0.36534675445388881 
		71 0.01553368453587846
		4 63 0.5053482745838962 69 0.12214847136565431 70 0.36688793388917917 
		71 0.005615320161270353
		4 63 0.54068817508369904 69 0.16780347190701786 70 0.2878309286105965 
		71 0.0036774243986866643
		3 63 0.53617150390403723 69 0.13975738197203549 70 0.32407111412392725
		4 63 0.5880064247770781 69 0.19867245445885323 70 0.21197832686498463 
		71 0.0013427938990840077
		3 63 0.56633859872817993 69 0.16621652245521545 70 0.26744487881660461
		3 63 0.61622034585147578 69 0.22305637265657824 70 0.16072328149194595
		3 63 0.58550393581390381 69 0.19819943606853485 70 0.21629662811756134
		3 63 0.60712596055589474 69 0.27244983138329654 70 0.12042420806080878
		3 63 0.62694742630971323 69 0.28178835964904575 70 0.091264214041241035
		4 63 0.62915999209987927 69 0.24359502096796076 70 0.12582589788453338 
		71 0.0014190890476266193
		3 63 0.59270619683668546 69 0.34592201919195781 70 0.061371783971356779
		3 63 0.57730984257675821 69 0.34030669674048797 70 0.082383460682753762
		3 63 0.5630273881892941 69 0.39662775840566783 70 0.040344853405038121
		3 63 0.55580985960222673 69 0.35498589541752557 70 0.089204244980247649
		3 63 0.58020905046720572 69 0.26474403151523929 70 0.15504691801755496
		3 63 0.56093691107818744 69 0.24669260541520699 70 0.19237048350660552
		3 63 0.55710689553299853 69 0.17547875119809059 70 0.26741435326891083
		3 63 0.53998626887757384 69 0.12938124327007661 70 0.3306324878523495
		3 63 0.5226978063583374 69 0.10533303022384644 70 0.37196916341781616
		3 63 0.52462042941511955 69 0.10374608945089846 70 0.37163348113398198
		3 63 0.54036773056339815 69 0.16115053238198954 70 0.29848173705461228
		3 63 0.51537347223887942 69 0.10865949920311196 70 0.37596702855800856
		3 63 0.54085601182067411 69 0.20383002167686853 70 0.25531396650245736
		3 63 0.55127793550491333 69 0.30843061208724976 70 0.14029145240783691
		3 63 0.53517968260019544 69 0.20032044053555192 70 0.26449987686425264
		3 63 0.5052567274944999 69 0.11900511738673203 70 0.37573815511876807
		3 63 0.53382162648970999 69 0.16597237688385316 70 0.30020599662643682
		3 63 0.54959946870803833 69 0.2858930230140686 70 0.16450750827789307
		3 63 0.54012358993476017 69 0.32205692413534109 70 0.13781948592989871
		3 63 0.53040360218874505 69 0.41150530252966355 70 0.058091095281591371
		3 63 0.5382620096206665 69 0.39119553565979004 70 0.070542454719543457
		3 63 0.56171511243601058 69 0.4112611611440869 70 0.027023726419902513
		3 63 0.55703060781526181 69 0.41051345298973002 70 0.032455939195008221
		3 63 0.62719158157139221 69 0.36272220553763063 70 0.010086212890977154
		3 63 0.59769588152229891 69 0.38803693290765462 70 0.014267185570046441
		4 1 0.0010070954247819711 63 0.7058976151265216 69 0.28889905827927426 
		70 0.0041962311694221845
		3 63 0.7419088957985811 69 0.2550698179158179 70 0.0030212862856010812
		4 1 0.0011291676124683906 63 0.83518731030159821 69 0.16241702327735405 
		70 0.0012664988085794111
		4 1 0.0016937514494624504 63 0.82505531060223236 69 0.17178607182985114 
		70 0.0014648661184540111
		3 1 0.0010376134645749475 63 0.92434576981827221 69 0.074616616717152834
		2 63 0.85502403974533081 69 0.14497596025466919
		2 63 0.86021210044938479 69 0.13978789955061524
		3 63 0.76040283860528957 69 0.23692683263242281 70 0.002670328762287625
		3 63 0.77248798308044142 69 0.22526894074461373 70 0.002243076174944797
		3 63 0.65476462907990818 69 0.3370565354748179 70 0.0081788354452739034
		3 63 0.65595484390812786 69 0.33487448408151499 70 0.0091706720103572302
		3 63 0.57740139746143893 69 0.4008544966546651 70 0.021744105883895956
		3 63 0.56632334099397685 69 0.40845349507118295 70 0.025223163934840195
		3 63 0.65825895125620049 69 0.33359273087557056 70 0.0081483178682289284
		3 63 0.53659875000415369 69 0.39803159830021262 70 0.065369651695633704
		3 63 0.75925840114035048 69 0.2378423846554005 70 0.0028992142042490042
		2 63 0.85854886683003806 69 0.14145113316996197
		2 63 0.924605176976246 69 0.075394823023754012
		2 63 0.93078507379867248 69 0.069214926201327534
		2 63 0.96530098442212475 69 0.034699015577875192
		2 63 0.97091630549574592 69 0.029083694504254083
		3 1 0.0013275349124307681 63 0.98869306424570425 69 0.0099794008418649955
		3 1 0.0010833905778721263 63 0.98580910909926689 69 0.013107500322861022
		3 1 0.0020752269354311881 63 0.99476615559666992 69 0.0031586174678989408
		3 1 0.0054779891613431775 63 0.99302662667432751 69 0.001495384164329326
		3 1 0.0044708937245528527 63 0.99333180708497615 69 0.0021972991904709816
		3 1 0.0020904860212634948 63 0.99287403670124053 69 0.0050354772774960097
		3 1 0.0050659952343176445 63 0.9917448692115487 69 0.0031891355541336978
		3 1 0.013122758702832948 63 0.98374914183893358 69 0.0031280994582334352
		3 1 0.011779965200465221 63 0.98603799461343822 69 0.0021820401860965372
		3 1 0.032791636212341491 63 0.96342412643569453 69 0.0037842373519640215
		3 1 0.03048752702448182 63 0.96662851776049463 69 0.0028839552150235629
		3 1 0.032471198830538978 63 0.96533150200047724 69 0.0021972991689838406
		3 1 0.068726634533162509 63 0.92796215780931035 69 0.0033112076575271491
		4 1 0.075745781912104848 63 0.92022583640565003 69 0.0029602501755892257 
		71 0.0010681315066559062
		4 1 0.12536812161374042 63 0.86855878751159221 69 0.004119936020502985 
		71 0.001953154854164378
		4 1 0.1406729257044729 63 0.85317768831652774 69 0.0039368277483420042 
		71 0.0022125582306573278
		4 1 0.18416113787011784 63 0.80772106241055519 69 0.0048065920340455313 
		71 0.0033112076852813703
		4 1 0.24148927066732964 63 0.74821088956177961 69 0.0053101394951776716 
		71 0.0049897002757131057
		4 1 0.22462806440335609 63 0.76661325643380374 69 0.004776074156553658 
		71 0.0039826050062865765
		4 1 0.084519723417436243 63 0.91154344884797101 69 0.0028381781342413149 
		71 0.0010986496003514766
		4 1 0.15034714390171228 63 0.84400701797942124 69 0.0036469062443488945 
		71 0.0019989318745175949
		4 1 0.16157777408053586 63 0.83079271483421002 69 0.0050202183737252902 
		71 0.0026092927115288298
		4 1 0.11900511292573793 63 0.87463187499371087 69 0.0046082245763224986 
		71 0.0017547875042287662
		4 1 0.15710688875048065 63 0.83501945584631931 69 0.0055390250910556105 
		71 0.0023346303121444091
		4 1 0.11824215934816497 63 0.87486076253133271 69 0.0052338447360859202 
		71 0.0016632333844163998
		3 1 0.067658504664012811 63 0.92829785440127077 69 0.004043640934716459
		4 1 0.11761654214921435 63 0.87533378947541918 69 0.005447471070244677 
		71 0.0016021973051217743
		4 1 0.15555046658129909 63 0.83634699247760413 69 0.0059052417659737726 
		71 0.0021972991751230239
		4 1 0.15288014464342733 63 0.83923094116455532 69 0.005828946269537021 
		71 0.002059967922480361
		3 1 0.069428548410800886 63 0.92588693162208502 69 0.0046845199671141429
		3 1 0.038635841620547583 63 0.959380485578606 69 0.0019836728008464132
		3 1 0.013672083702205275 63 0.98478675507689883 69 0.0015411612208959071
		3 63 0.49643702424549363 69 0.10032806769746694 70 0.40323490805703943
		3 63 0.48291751382561388 69 0.066651410857950066 70 0.450431075316436
		3 63 0.48821241027275031 69 0.073762111915365691 70 0.43802547781188395
		3 63 0.49346151212660205 69 0.049912258238907783 70 0.45662622963449018
		3 63 0.49761196970939636 69 0.072388797998428345 70 0.42999923229217529
		3 63 0.50377661365104176 69 0.046478979635827089 70 0.4497444067131311
		3 63 0.51743342612597232 69 0.03831540577661046 70 0.44425116809741722
		3 63 0.52364385030484972 69 0.029419394155183073 70 0.4469367555399672
		3 63 0.54586100273284499 69 0.019867246859517431 70 0.43427175040763755
		3 63 0.54465552010349816 69 0.025192645291737495 70 0.43015183460476442
		3 63 0.50345617157626021 69 0.068833447479952514 70 0.42771038094378722
		3 63 0.51096361494836495 69 0.1213702624934147 70 0.36766612255822029
		3 63 0.50910199636783449 69 0.037766081053131839 70 0.45313192257903373
		3 63 0.50122834745730005 69 0.041046769650184202 70 0.45772488289251573
		3 63 0.49005875539100269 69 0.050034333579625938 70 0.45990691102937137
		3 63 0.49787137283288962 69 0.042435340899492358 70 0.45969328626761796
		4 63 0.59081406034004103 69 0.22043183682017597 70 0.18361181217388794 
		71 0.0051422906658950655
		4 63 0.5157244147838157 69 0.098710610359416043 70 0.38385596442383568 
		71 0.0017090104329324093
		4 63 0.52468145577753 69 0.18487830701125441 70 0.27472344399069271 
		71 0.015716793220522912
		4 63 0.4641031536440709 69 0.15494011053927037 70 0.33376058314441548 
		71 0.047196152672243252
		4 1 0.015716793220522912 63 0.6030365307279969 69 0.35683224070412234 
		70 0.024414435347357853
		4 63 0.56037230343320044 69 0.35681698390873118 70 0.048310064679199169 
		71 0.034500647978869231
		4 63 0.5070878267288208 69 0.32671090960502625 70 0.078263521194458008 
		71 0.087937742471694946
		4 63 0.43192187595251019 69 0.27199206161487194 71 0.17613488698206672 
		77 0.11995117545055115
		4 63 0.45387959480285645 69 0.28657969832420349 71 0.1424277126789093 
		77 0.11711299419403076
		4 1 0.096467541105561577 63 0.5670862878424866 69 0.26794842284840975 
		71 0.068497748203542055
		4 1 0.079499504571786103 63 0.68671702571156967 69 0.20624093480883984 
		71 0.027542534907804412
		3 1 0.0074311436871678472 63 0.93176165600041894 69 0.060807200312413268
		3 1 0.0067444875354403912 63 0.97132829776509977 69 0.021927214699459886
		3 1 0.012939650938966478 63 0.97843900167533115 69 0.0086213473857024402
		3 1 0.0051575495415811532 63 0.98617532578499256 69 0.0086671246734263165
		3 1 0.0087739376702179704 63 0.98716716257613857 69 0.0040588997536435299
		3 71 0.5505149981026165 77 0.062226291977712109 78 0.38725870991967137
		2 71 0.58338291539592513 77 0.051453423713397679;
	setAttr ".wl[1113:1273].w"
		1 78 0.3651636608906772
		3 71 0.65033950359641024 77 0.14287022181958622 78 0.20679027458400354
		3 71 0.63978027344077415 77 0.2160219666954582 78 0.14419775986376762
		4 1 0.41969939675462065 63 0.5660029000974921 69 0.0080720222734657829 
		71 0.0062256808744214397
		4 1 0.61751736144968972 63 0.36591134029073574 69 0.0030365454026906403 
		71 0.013534752856883905
		4 1 0.81881437607790186 63 0.12249942558062324 69 0.0016632333441422241 
		71 0.057022964997332733
		4 1 0.1714503708421363 63 0.0052643626119151035 71 0.81466391969419161 
		77 0.0086213468517569707
		4 1 0.13815517601326652 63 0.0037537193525020648 71 0.85052262984219473 
		77 0.007568474792036684
		4 1 0.093202106893347389 63 0.0022430762240369427 71 0.89866483441677714 
		77 0.0058899824658385025
		4 1 0.087693599539488382 63 0.0019684137724268352 71 0.90472266677914626 
		77 0.0056153199089385682
		4 1 0.13351644553835151 63 0.0035248340515713584 71 0.85564964870234317 
		77 0.0073090717077340227
		4 1 0.082505532070093965 63 0.0018005645934523898 71 0.91053635390775101 
		77 0.0051575494287026081
		4 1 0.13043412399155163 63 0.003463797925387303 71 0.85897611471738522 
		77 0.0071259633656758853
		4 1 0.081849397448441344 63 0.0017700465659804131 71 0.91132981943085523 
		77 0.0050507365547230324
		4 1 0.13116654613202877 63 0.0033875028239970257 71 0.85838102375028491 
		77 0.0070649272936893033
		4 1 0.16313420053794012 63 0.0048065920754530424 71 0.82348363671283831 
		77 0.0085755706737685507
		4 1 0.16523994782410475 63 0.0048676282983434477 71 0.8212252992969522 
		77 0.0086671245805995927
		4 1 0.16498054971171969 63 0.0046692608145395406 71 0.82200350405936395 
		77 0.0083466854143768206
		4 1 0.14288547468737844 63 0.0035095749945662103 71 0.84660105911780781 
		77 0.0070038912002475563
		4 1 0.092484931682210988 63 0.0019226368212069279 71 0.90037384583902047 
		77 0.0052185856575616618
		4 1 0.17676051430187623 63 0.0048523690908146271 71 0.81033035283388111 
		77 0.0080567637734280592
		3 1 0.048935680373762239 71 0.94749370859136495 77 0.0035706110348727627
		3 1 0.040314334963022093 71 0.95632868025487716 77 0.0033569847821008111
		3 1 0.024261845400035519 71 0.97302204868907227 77 0.0027161059108922097
		3 1 0.018539711397022277 71 0.9789425500498159 77 0.0025177385531618274
		3 1 0.02427710417221882 71 0.97296101285290426 77 0.0027618829748769702
		3 1 0.013000686725605391 71 0.98474097802158989 77 0.0022583352528046923
		3 1 0.0131990537662015 71 0.98466468315881073 77 0.0021362630749878616
		3 1 0.0062104221230964386 71 0.99198901329938183 77 0.0018005645775217786
		3 1 0.013168536252321207 71 0.98501564012506082 77 0.0018158236226180496
		3 1 0.0064545664786022005 71 0.99205004937935148 77 0.0014953841420463655
		3 1 0.019256885624031307 71 0.97889677277203624 77 0.0018463416039324672
		3 1 0.0095826657890547024 71 0.98855573353217985 77 0.0018616006787654041
		3 1 0.033554587130394123 71 0.96398871037283751 77 0.0024567024967683429
		3 1 0.019958801683729991 71 0.97700465294185945 77 0.0030365453744106074
		3 1 0.060456244645555983 71 0.93597314431957124 77 0.0035706110348727627
		3 1 0.042343783926480527 71 0.95271229300316285 77 0.0049439230703566079
		3 1 0.013992522784540102 71 0.98017853087670781 77 0.0058289463387520436
		3 1 0.0057679104448195347 71 0.99020370765721133 77 0.0040283818979691991
		3 1 0.0024414435188193848 71 0.98870832372546036 77 0.0088502327557202706
		3 1 0.0015411612094133613 71 0.97645532971195026 77 0.022003509078636407
		2 71 0.98112458904389843 77 0.018875410956101592
		2 71 0.95799191233503689 77 0.042008087664963119
		3 1 0.0010528725290124862 71 0.94642557366330127 77 0.052521553807686208
		3 1 0.0018158235617378199 71 0.94769207350623708 77 0.050492102932025072
		2 71 0.89088273712160237 77 0.10911726287839757
		3 1 0.0013122758956429521 71 0.88723582896960551 77 0.11145189513475159
		3 1 0.0030212862968562498 71 0.94842450618396434 77 0.048554207519179396
		3 1 0.0019073776953420309 71 0.90484474130194614 77 0.093247881002711849
		4 1 0.0016174563451517984 71 0.82160676769084295 77 0.175478759083459 
		78 0.0012970168805462535
		3 71 0.79090561231971557 77 0.20761426252391071 78 0.0014801251563736912
		3 71 0.68294803745905885 77 0.31361868269252308 78 0.0034332798484181647
		4 1 0.0012207217491777209 71 0.71931028232106886 77 0.27666133590664466 
		78 0.002807660023108758
		3 71 0.60642405114988396 77 0.3857022933259337 78 0.0078736555241824321
		3 71 0.63819332535492235 77 0.3576104432861153 78 0.0041962313589623632
		3 71 0.57663844673339171 77 0.41400777329672656 78 0.0093537799698817543
		3 71 0.59681086565085861 77 0.3940947574786936 78 0.0090943768704478505
		3 71 0.69173722815013283 77 0.30569925619569366 78 0.0025635156541735341
		3 71 0.7312275784351574 77 0.26697185697725939 78 0.0018005645875832173
		3 71 0.77950713604817889 77 0.21943999147379797 78 0.0010528724780231621
		2 71 0.81625086069107056 77 0.18374913930892944
		2 71 0.86442358589803558 77 0.13557641410196444
		2 71 0.92901503347594261 77 0.070984966524057336
		2 71 0.87728695100649556 77 0.12271304899350444
		2 71 0.92930495046597006 77 0.070695049534029886
		2 71 0.96697947841563692 77 0.03302052158436309
		2 71 0.98573281400475832 77 0.014267185995241712
		2 71 0.98689250024172714 77 0.013107499758272903
		3 1 0.0018158236319191961 71 0.99316395785876765 77 0.0050202185093131306
		3 1 0.001419089048948249 71 0.9927977413682062 77 0.0057831695828455534
		3 1 0.0039215689305873531 71 0.99339284316744692 77 0.0026855879019656815
		3 1 0.0024719614925877236 71 0.99075303293513484 77 0.0067750055722774647
		3 1 0.0012359807592437003 71 0.97976653650203716 77 0.018997482738719169
		3 1 0.0016327153870434733 71 0.96278324365747148 77 0.035584040955485029
		3 1 0.0013122758858657346 71 0.92607003666011167 77 0.072617687454022667
		2 71 0.94431983017444865 77 0.055680169825551365
		3 71 0.87809567498663488 77 0.12056153110427648 78 0.0013427939090886016
		3 71 0.88169680609435785 77 0.11725032141192998 78 0.0010528724937121845
		2 71 0.96456855176177414 77 0.035431448238225846
		2 71 0.92075990258515028 77 0.079240097414849733
		3 71 0.80007630251316042 77 0.1976958802997773 78 0.0022278171870622997
		3 71 0.80027466695647009 77 0.19653619748048592 78 0.0031891355630440394
		3 71 0.70908675035476698 77 0.2846570508933659 78 0.0062561987518671416
		3 71 0.71400016612745842 77 0.28215456035188824 78 0.0038452735206533908
		3 71 0.60735484353164537 77 0.37563134709048696 78 0.017013809377867724
		3 71 0.62459755060188016 77 0.36574348875459933 78 0.0096589606435205054
		3 71 0.75194933218734028 77 0.24605173588648135 78 0.0019989319261783946
		2 71 0.85000381320703589 77 0.14999618679296414
		3 71 0.78619057928544733 77 0.2126802530802632 78 0.0011291676342894911
		3 71 0.6451209226560648 77 0.34943160626227543 78 0.0054474710816597213
		3 71 0.66730755816142096 77 0.32903027657058193 78 0.0036621652679971056
		3 71 0.57352560224453364 77 0.41026931619020818 78 0.016205081565258263
		3 71 0.58660256644113895 77 0.40144961922820799 78 0.011947814330653048
		3 71 0.56549935900979464 77 0.39285876907938605 78 0.041641871910819354
		3 71 0.57708096289232014 77 0.38942548487549467 78 0.033493552232185184
		3 71 0.579980149007853 77 0.39035631171359131 78 0.029663539278555681
		3 71 0.61390096406564831 77 0.31229114765145738 78 0.073807888282894252
		3 71 0.59858090131417585 77 0.31808957694537621 78 0.083329521740447887
		3 71 0.63030440554476386 77 0.23337148477690645 78 0.13632410967832967
		3 71 0.59958799480164038 77 0.23653010238796779 78 0.16388190281039186
		3 71 0.58866255598273043 77 0.18631265779863806 78 0.22502478621863148
		3 71 0.56403447878463508 77 0.25857938106594625 78 0.17738614014941873
		3 71 0.57312886198971091 77 0.32535286768219268 78 0.10151827032809643
		3 71 0.54653239657381469 77 0.33096817382401356 78 0.12249942960217169
		3 71 0.54615091260241511 77 0.3979858085888287 78 0.055863278808756196
		3 71 0.52841991973549007 77 0.39465934626250487 78 0.076920734002005067
		3 71 0.55652703202301901 77 0.41771573839765896 78 0.02575722957932201
		3 71 0.53702601010831486 77 0.41884489583706058 78 0.044129094054624569
		3 1 0.0028381780047216087 71 0.98281834175636273 77 0.014343480238915657
		3 1 0.0050354771696339761 71 0.99147020685507459 77 0.0034943159752914565
		3 1 0.0055848019764818124 71 0.98785381865224176 77 0.0065613793712764462
		3 1 0.0084534986692557466 71 0.98889143149784642 77 0.0026550698328978973
		3 1 0.0069581138455682258 71 0.99089036411007847 77 0.002151522044353333
		3 1 0.002960250169386093 71 0.99436942106956983 77 0.0026703287610441561
		3 1 0.011596856930400372 71 0.98602273559441223 77 0.0023804074751874447
		3 1 0.0094758520980593158 71 0.98644998893747138 77 0.004074158964469313
		3 1 0.014053558649354139 71 0.98304722724900084 77 0.002899214101645068
		3 1 0.0014648660758207967 71 0.99102769528559764 77 0.0075074386385815834
		3 1 0.0030823225114047508 71 0.99407949933452955 77 0.0028381781540657604
		3 1 0.083787289901060338 71 0.90853742206830279 77 0.0076752880306368313
		4 1 0.10086213978156093 63 0.0013275349285034905 71 0.88422979509590527 
		77 0.013580530194030336
		4 1 0.14514382176793003 63 0.001556420232375888 71 0.84406804999147167 
		77 0.0092317080082224175
		4 1 0.17856107257229697 63 0.0030975813757930346 71 0.80340276371611685 
		77 0.014938582335793106
		4 1 0.12385748107611003 63 0.0032349125841042593 71 0.84661631278161897 
		77 0.026291293558166756
		4 1 0.21615930022388305 63 0.0086823832728846924 71 0.74613565623463496 
		77 0.029022660268597268
		4 1 0.13968108386276537 63 0.0090028232484635224 71 0.7959105849875423 
		77 0.055405507901228848
		4 1 0.23845273389547728 63 0.023819333075467495 71 0.67986572168692416 
		77 0.057862211342131036
		4 1 0.1063553854531999 63 0.0010833905692957443 71 0.88772411373809978 
		77 0.0048371102394046041
		4 1 0.091660948016127244 63 0.0012054627480824808 71 0.90348668294728762 
		77 0.0036469062885026949
		3 1 0.027115282132154236 71 0.96984817245949917 77 0.0030365454083466472
		3 1 0.046189059152782243 71 0.94999618532596952 77 0.0038147555212482806
		4 1 0.053620203855082454 63 0.0010681315230696932 71 0.94093232514443148 
		77 0.0043793394774163837
		4 1 0.16729990896475633 63 0.0049134049786647991 71 0.81907378444853829 
		77 0.00871290160804058
		3 71 0.60756847752908894 77 0.045609215268115073 78 0.34682230720279594
		3 71 0.63266957395402312 77 0.028686961426278218 78 0.33864346461969863
		3 71 0.62951094615657943 77 0.032425422583804535 78 0.33806363125961608
		3 71 0.67437247035451808 77 0.019913022632994819 78 0.30571450701248715
		3 71 0.66884869212499132 77 0.015701534197290364 78 0.31544977367771831
		3 71 0.70064849379205463 77 0.012985427996925737 78 0.28636607821101961
		3 71 0.70832378463808954 77 0.016784925201366752 78 0.27489129016054376
		3 71 0.67637140314696065 77 0.022735942409216715 78 0.30089265444382268
		3 71 0.69350729822723645 77 0.021011672444380691 78 0.28548102932838287
		3 71 0.6874036782538484 77 0.0098268100900325839 78 0.30276951165611904
		3 71 0.59598688606209438 77 0.019348440151239554 78 0.38466467378666602
		3 71 0.56310367898887215 77 0.021118486418119555 78 0.41577783459300827
		4 63 0.364644855260849 70 0.19891661405563354 71 0.2857099175453186 
		78 0.15072861313819885
		4 63 0.41376364231109619 70 0.25645837187767029 71 0.21052873134613037 
		78 0.11924925446510315
		4 63 0.45357442578039209 70 0.23448539129622864 71 0.20830090654344718 
		78 0.10363927637993212
		3 0 0.46065460949160741 63 0.16914625213822346 71 0.3701991383701691
		3 0 0.44310673411031465 63 0.19044784917760121 71 0.36644541671208414
		3 0 0.45120927691459656 63 0.18956282734870911 71 0.35922789573669434
		3 0 0.45021745562553406 63 0.21316853165626526 71 0.33661401271820068
		3 0 0.4680247237082612 63 0.18059052257849986 71 0.35138475371323891
		3 0 0.47162583470344543 63 0.20308232307434082 71 0.32529184222221375
		3 0 0.49243914347232665 63 0.16858167695132378 71 0.33897917957634954
		3 0 0.48334477792217667 63 0.15260547854320641 71 0.36404974353461694
		3 0 0.50519568480842836 63 0.13922332434688992 71 0.3555809908446817
		3 0 0.51691460609436035 63 0.15590143203735352 71 0.32718396186828613
		3 0 0.52350652997950509 63 0.1261768508877881 71 0.35031661913270679
		3 0 0.48981460199036297 63 0.13159380657086064 71 0.37859159143877641
		3 0 0.50485999896705147 63 0.11937132833514597 71 0.37576867269780256;
	setAttr ".wl[1274:1440].w"
		3 0 0.53484397728112354 63 0.11763179959631115 71 0.34752422312256526
		3 0 0.54421301317849791 63 0.13862821872914488 71 0.31715876809235716
		3 0 0.54967576265335083 63 0.13492026925086975 71 0.31540396809577942
		3 0 0.5383535543329484 63 0.16856641816248866 71 0.29308002750456291
		3 0 0.53075455828376772 63 0.17314411441767044 71 0.29610132729856181
		3 0 0.52202641186078769 63 0.22178987828210178 71 0.25618370985711053
		3 0 0.50954451454629812 63 0.22403296339659229 71 0.26642252205710959
		3 0 0.49861904978752136 63 0.2846875786781311 71 0.21669337153434753
		3 0 0.48148319125175476 63 0.28194093704223633 71 0.23657587170600891
		3 0 0.4917219877243042 63 0.22827497124671936 71 0.28000304102897644
		3 0 0.51692988028913378 63 0.18200961297779122 71 0.301060506733075
		3 0 0.49591820693137934 63 0.19407950052500517 71 0.3100022925436155
		3 0 0.53527122735977173 63 0.14493018388748169 71 0.31979858875274658
		3 0 0.47058823704719543 63 0.23405814170837402 71 0.29535362124443054
		3 0 0.45040054767130172 63 0.24193178886378441 71 0.30766766346491387
		3 0 0.44731822609901428 63 0.28172731399536133 71 0.27095445990562439
		3 0 0.43480584025382996 63 0.28801402449607849 71 0.27718013525009155
		3 0 0.4368352824921119 63 0.24908826874064999 71 0.31407644876723811
		3 0 0.43872740864753723 63 0.21695277094841003 71 0.34431982040405273
		3 0 0.43089951780737884 63 0.21844815556859506 71 0.35065232662402612
		3 0 0.43978026509284973 63 0.18788433074951172 71 0.37233540415763855
		3 0 0.42938887433128248 63 0.19658197169628783 71 0.3740291539724297
		3 0 0.41632714867591858 63 0.2379491925239563 71 0.34572365880012512
		3 0 0.41832607984542847 63 0.26272985339164734 71 0.31894406676292419
		3 0 0.42854961752891541 63 0.25687038898468018 71 0.31457999348640442
		3 0 0.42487221956253052 63 0.29701685905456543 71 0.27811092138290405
		3 0 0.41301594415354564 63 0.2894789066755446 71 0.29750514917090981
		3 0 0.40750744938850403 63 0.2542153000831604 71 0.33827725052833557
		3 0 0.41760891675949097 63 0.20317387580871582 71 0.37921720743179321
		3 0 0.40923172235488892 63 0.21712061762809753 71 0.37364766001701355
		3 0 0.41953154773218115 63 0.18023957043529196 71 0.40022888183252692
		3 0 0.42775616049766541 63 0.16253909468650818 71 0.40970474481582642
		3 0 0.43625542521476746 63 0.15231555700302124 71 0.4114290177822113
		3 0 0.43811702728271484 63 0.17543298006057739 71 0.38644999265670776
		3 0 0.44335088133811951 63 0.14058136940002441 71 0.41606774926185608
		3 0 0.44310673080891227 63 0.11841001096941506 71 0.43848325822167267
		3 0 0.44962232969982674 63 0.10592812965863846 71 0.44444954064153475
		3 0 0.45619898014815941 63 0.093064775472921676 71 0.4507362443789189
		3 0 0.45497825402782666 63 0.090424961668066961 71 0.45459678430410633
		3 0 0.44814221072514826 63 0.10395971918016045 71 0.44789807009469129
		3 0 0.44890516996383667 63 0.10359349846839905 71 0.44750133156776428
		3 0 0.43967346012105735 63 0.12214847091061579 71 0.43817806896832689
		3 0 0.43656062429307962 63 0.13369954923243002 71 0.42973982647449038
		3 0 0.42783245444297791 63 0.15033188462257385 71 0.42183566093444824
		3 0 0.43076218870990907 63 0.14021515428378717 71 0.42902265700630376
		3 0 0.43953612119305041 63 0.12141603886026114 71 0.43904783994668839
		3 0 0.43085375428199768 63 0.13910123705863953 71 0.43004500865936279
		3 0 0.42409399783751367 63 0.15368886520994998 71 0.42221713695253638
		3 0 0.42049285769462585 63 0.16427862644195557 71 0.41522851586341858
		3 0 0.42490273080911145 63 0.15135423613556867 71 0.42374303305531991
		3 0 0.42607766389846802 63 0.15190356969833374 71 0.42201876640319824
		3 0 0.43459221720695496 63 0.13493552803993225 71 0.43047225475311279
		3 0 0.42058441669619706 63 0.16319523994915544 71 0.41622034335464753
		3 0 0.4130159318447113 63 0.19325551390647888 71 0.39372855424880981
		3 0 0.41515221573185601 63 0.18466467880212248 71 0.40018310546602154
		3 0 0.4237277868945567 63 0.17102311806415196 71 0.40524909504129136
		3 0 0.41358053067951606 63 0.19224841606246806 71 0.39417105325801594
		3 0 0.42236971855163574 63 0.17921721935272217 71 0.39841306209564209
		3 0 0.43280690908432007 63 0.1581445038318634 71 0.40904858708381653
		3 0 0.4452124800889754 63 0.1174639529178742 71 0.43732356699315034
		3 0 0.44196230831686123 63 0.14377050315991793 71 0.41426718852322086
		3 0 0.45275044778548512 63 0.10305943416848357 71 0.44419011804603126
		3 0 0.4563515714354579 63 0.089036388858610552 71 0.45461203970593156
		3 0 0.46433204758414659 63 0.073853664650422812 71 0.46181428776543054
		3 0 0.46163118573473672 63 0.077378497680701278 71 0.46099031658456202
		3 0 0.46839094510965751 63 0.064148925722754935 71 0.4674601291675875
		3 0 0.46373692500395269 63 0.079667352733517827 71 0.45659572226252942
		3 0 0.47110704640538348 63 0.066987106211195274 71 0.46190584738342122
		3 0 0.4742351490044413 63 0.052582588242674574 71 0.47318226275288411
		3 0 0.47423514547111412 63 0.058884564567787331 71 0.46688028996109854
		3 0 0.47263294106250298 63 0.0904707380349134 71 0.43689632090258357
		3 0 0.47493705861176638 63 0.08305485670350278 71 0.44200808468473085
		3 0 0.48783093327409821 63 0.11560235086379683 71 0.3965667158621049
		3 0 0.47727168317543989 63 0.12776379477625779 71 0.39496452204830235
		3 0 0.46916913986206055 63 0.099702447652816772 71 0.43112841248512268
		3 0 0.46425574326134111 63 0.1432974764213342 71 0.39244678031732472
		3 0 0.4727855254294645 63 0.14708171565708941 71 0.38013275891344611
		3 0 0.45485618710517883 63 0.16594186425209045 71 0.37920194864273071
		3 0 0.45046158953813331 63 0.15739680592124453 71 0.39214160454062219
		3 0 0.45247578620910645 63 0.1268482506275177 71 0.42067596316337585
		3 0 0.4628213873085173 63 0.11210803520518489 71 0.42507057748629784
		3 0 0.49489584565162659 63 0.10740825533866882 71 0.39769589900970459
		3 0 0.51480889320373535 63 0.10933089256286621 71 0.37586021423339844
		3 0 0.49930572509765625 63 0.099549859762191772 71 0.40114441514015198
		3 0 0.47618829494434156 63 0.076966508076093967 71 0.44684519697956449
		3 0 0.47186999809935692 63 0.075104906035886612 71 0.45302509586475648
		3 0 0.49524682760238647 63 0.097657740116119385 71 0.40709543228149414
		3 0 0.44942396879196167 63 0.07623407244682312 71 0.47434195876121521
		3 0 0.44740976883300165 63 0.050171664725877391 71 0.50241856644112093
		3 0 0.41029983453229191 63 0.078675515363547832 71 0.51102465010416021
		3 0 0.42572671809385298 63 0.10260166380705929 71 0.47167161809908775
		3 0 0.37105363330950114 63 0.10963607497784439 71 0.51931029171265441
		3 0 0.37991913303913621 63 0.1225452023175686 71 0.49753566464329513
		3 0 0.31725030664726633 63 0.13383687833194616 71 0.54891281502078748
		3 0 0.3961089551448822 63 0.15045395493507385 71 0.45343708992004395
		3 0 0.45914396643638611 63 0.13063248991966248 71 0.41022354364395142
		3 0 0.41733425233760102 63 0.19612420803123404 71 0.386541539631165
		3 0 0.35330739617347717 63 0.23279163241386414 71 0.41390097141265869
		3 0 0.43073168396949768 63 0.26019683480262756 71 0.30907148122787476
		3 0 0.48325321798403886 63 0.21779202249336277 71 0.29895475952259837
		3 0 0.48267338399102366 63 0.29527733169909315 71 0.22204928430988319
		3 0 0.51577019691467285 63 0.25995269417762756 71 0.22427710890769958
		3 0 0.50437171018677518 63 0.34222934159978241 71 0.15339894821344238
		3 0 0.52188908276127155 63 0.31857785107824427 71 0.15953306616048415
		3 0 0.53267718948951925 63 0.237552456186785 71 0.22977035432369572
		3 0 0.52040893614901507 63 0.18887616975420968 71 0.29071489409677526
		3 0 0.54058136166874649 63 0.17340353648077061 71 0.2860151018504829
		3 0 0.53408103385446914 63 0.22670328279281732 71 0.23921568335271354
		3 0 0.52483405246836112 63 0.30547035650820603 71 0.16969559102343293
		3 0 0.52117187561350875 63 0.29631495917312739 71 0.18251316521336383
		3 0 0.53003739520851678 63 0.22093537120617374 71 0.24902723358530948
		3 0 0.54280918836593628 63 0.16818493604660034 71 0.28900587558746338
		3 0 0.51274890471620715 63 0.28949416115126253 71 0.19775693413253032
		3 0 0.54708170890808105 63 0.13644617795944214 71 0.31647211313247681
		3 0 0.52208744701612819 63 0.1451285608838713 71 0.33278399210000048
		3 0 0.53775845355515317 63 0.11129930283727339 71 0.35094224360757342
		3 0 0.54074920432454054 63 0.11190966766870769 71 0.34734112800675171
		3 0 0.52008849769896637 63 0.10113679692996141 71 0.37877470537107216
		3 0 0.51670099459665253 63 0.099885562804763683 71 0.38341344259858373
		3 0 0.51017014651983539 63 0.11700617918353738 71 0.37282367429662722
		3 0 0.48972304925735222 63 0.10260166074929147 71 0.40767528999335634
		3 0 0.47008468650092139 63 0.099229415523348408 71 0.4306858979757302
		3 0 0.44031432599063458 63 0.11081101827927692 71 0.44887465573008845
		3 0 0.47640193218591709 63 0.16536201783064033 71 0.35823604998344255
		3 0 0.47080186009407043 63 0.37845426797866821 71 0.15074387192726135
		3 0 0.43216601014137268 63 0.34734112024307251 71 0.22049286961555481
		3 0 0.42024871706962585 63 0.42940413951873779 71 0.15034714341163635
		3 0 0.36801707744598389 63 0.4113832414150238 71 0.22059968113899231
		3 0 0.36842909455299377 63 0.31442740559577942 71 0.31714349985122681
		3 0 0.30083161592483521 63 0.37550926208496094 71 0.32365912199020386
		3 0 0.28928053379058838 63 0.27104601263999939 71 0.43967345356941223
		3 0 0.22987715557400651 63 0.3039902403356099 71 0.4661326040903836
		3 0 0.26761272948403253 63 0.18849470002196284 71 0.54389257049400463
		3 0 0.33057144776838193 63 0.17099260048557222 71 0.49843595174604582
		3 0 0.25624475264913965 63 0.14152743133198367 71 0.60222781601887665
		3 0 0.31232166522980975 63 0.11651789483813862 71 0.57116043993205157
		3 0 0.2542000431880358 63 0.12083619177964472 71 0.62496376503231943
		3 0 0.30470741249184924 63 0.088899062408492893 71 0.60639352509965783
		3 0 0.24989700689758371 63 0.092805372071346218 71 0.65729762103107003
		3 0 0.20144960434324743 63 0.12266727628310975 71 0.67588311937364276
		3 0 0.20251772694236853 63 0.14699016073375462 71 0.65049211232387683
		3 0 0.15730525787629571 63 0.15007248744476567 71 0.69262225467893856
		3 0 0.16502631708901175 63 0.21190203094774393 71 0.62307165196324432
		3 0 0.125368122022394 63 0.21272603311318258 71 0.66190584486442339
		3 0 0.12034790217876434 63 0.14932478964328766 71 0.730327308177948
		3 0 0.15617608558606846 63 0.12283512583866341 71 0.72098878857526816
		3 0 0.11923399301095322 63 0.12040894209424535 71 0.76035706489480137
		3 0 0.15355153725038925 63 0.095323110267291442 71 0.75112535248231926
		3 0 0.19891660960950086 63 0.095017930231587652 71 0.70606546015891147
		3 0 0.14818036335437948 63 0.075303270290743254 71 0.77651636635487731
		3 0 0.11119249711615958 63 0.074662396490478442 71 0.81414510639336202
		3 0 0.10049592033398091 63 0.062851913741617749 71 0.83665216592440128
		3 0 0.072510875221260818 63 0.060578315998775389 71 0.86691080877996374
		3 0 0.091752500025574113 63 0.060013734251363082 71 0.84823376572306275
		3 0 0.12539864006857485 63 0.060303656543541362 71 0.81429770338788376
		3 0 0.093705656936933307 63 0.068543525592789811 71 0.83775081747027691
		3 0 0.066514075297967157 63 0.066041045382924712 71 0.86744487931910808
		3 0 0.10557717084884644 63 0.093781948089599609 71 0.80064088106155396
		3 0 0.12991531096461928 63 0.0697642485069912 71 0.80032044052838947
		3 0 0.14782939741142542 63 0.095063708014311576 71 0.75710689457426295
		3 0 0.17378499974470585 63 0.068665600801515569 71 0.75754939945377853
		3 0 0.16783398264770222 63 0.059098191118998888 71 0.77306782623329884
		3 0 0.21452659208680247 63 0.055237657910304827 71 0.73023575000289265
		3 0 0.22702372158700124 63 0.058258947202037822 71 0.71471733121096093
		3 0 0.28062868640997796 63 0.053421837341447127 71 0.66594947624857492
		3 0 0.26717021862290635 63 0.049393452335942889 71 0.6834363290411507
		2 0 0.22207979526996918 63 0.06465247177105439;
	setAttr ".wl[1440:1607].w"
		1 71 0.71326773295897639
		3 0 0.27649347841207583 63 0.057373919967140558 71 0.66613260162078358
		3 0 0.32840466376988342 63 0.043274584996422436 71 0.62832075123369413
		3 0 0.33891815073385145 63 0.050614174643956775 71 0.61046767462219176
		3 0 0.39020372309246043 63 0.03755245441688123 71 0.57224382249065842
		3 0 0.33975737780694099 63 0.047913327099184291 71 0.61232929509387468
		3 0 0.39896237998814277 63 0.042710002670846889 71 0.55832761734101033
		3 0 0.44795911192741661 63 0.038681620310307308 71 0.51335926776227603
		3 0 0.44539558057867773 63 0.032379645251116806 71 0.52222477417020552
		3 0 0.47905698954005155 63 0.030457008970420908 71 0.49048600148952753
		3 0 0.45015638395910884 63 0.040009155273301074 71 0.50983446076759009
		3 0 0.4806439316320712 63 0.038574807633271868 71 0.48078126073465688
		3 0 0.48506904100132214 63 0.030594339879176952 71 0.48433661911950093
		3 0 0.47663080869850072 63 0.036911573398528894 71 0.48645761790297037
		3 0 0.48139162306164573 63 0.037216753876708565 71 0.48139162306164573
		3 0 0.48435187700652982 63 0.032761119550176854 71 0.48288700344329327
		3 0 0.48621347184320185 63 0.039581902030245197 71 0.4742046261265529
		3 0 0.48607614636421204 63 0.042969405651092529 71 0.47095444798469543
		3 0 0.48137635709906157 63 0.067505911998538851 71 0.45111773090239959
		3 0 0.47951477051504299 63 0.075303270290743254 71 0.44518195919421377
		3 0 0.47862973096028372 63 0.084733350802461041 71 0.43663691823725526
		3 0 0.47441824917183628 63 0.095948732674503823 71 0.42963301815365984
		3 0 0.47496756911277771 63 0.085831999778747559 71 0.43920043110847473
		3 0 0.46781109717910518 63 0.1091172596264498 71 0.42307164319444501
		3 0 0.47158007239043931 63 0.12907606747973166 71 0.39934386012982903
		3 0 0.46155489866599136 63 0.14303806850427594 71 0.39540703282973266
		3 0 0.4703746069911926 63 0.13411153653097843 71 0.395513856477829
		3 0 0.45653467690147942 63 0.14984358623856922 71 0.39362173685995139
		3 0 0.45770962410299848 63 0.12530708686432501 71 0.41698328903267651
		3 0 0.44705882668495178 63 0.1425345242023468 71 0.41040664911270142
		3 0 0.45125506000600846 63 0.11042954192205581 71 0.43831539807193576
		3 0 0.44274052317827162 63 0.12765697944675417 71 0.42960249737497425
		3 0 0.44870680236289795 63 0.10394445729297058 71 0.44734874034413141
		3 0 0.44032958149909973 63 0.12094300985336304 71 0.43872740864753723
		3 0 0.45775539706100665 63 0.084504464667390242 71 0.45774013827160309
		3 0 0.44972915127469826 63 0.10054169745060351 71 0.44972915127469826
		3 0 0.46349278783042414 63 0.073029683128441616 71 0.46347752904113426
		3 0 0.46994735740242843 63 0.060105285195143104 71 0.46994735740242843
		3 0 0.47299916080757037 63 0.054001678384859246 71 0.47299916080757037
		3 0 0.47858396172523499 63 0.042847335338592529 71 0.47856870293617249
		3 0 0.47621881429606511 63 0.047562371407869779 71 0.47621881429606511
		3 0 0.48378728919127417 63 0.032440680406229938 71 0.48377203040249589
		3 0 0.48551155941253477 63 0.028976881174930455 71 0.48551155941253477
		3 0 0.48953994105581317 63 0.020920117888373703 71 0.48953994105581317
		3 0 0.49031815024152053 63 0.019363699516958929 71 0.49031815024152053
		3 0 0.4932173650744176 63 0.013565269851164803 71 0.4932173650744176
		3 0 0.49253070859037135 63 0.014953841608476133 71 0.49251544980115253
		3 0 0.48816662844953451 63 0.023666743100930962 71 0.48816662844953451
		3 0 0.49124895153802955 63 0.017502096923940901 71 0.49124895153802955
		3 0 0.48690012913588648 63 0.026199741728226981 71 0.48690012913588648
		3 0 0.48212405680027559 63 0.035751886399448762 71 0.48212405680027559
		3 0 0.47981994450427695 63 0.040360110991446096 71 0.47981994450427695
		3 0 0.47321278738254285 63 0.053574425234914298 71 0.47321278738254285
		3 0 0.46523231614554161 63 0.069779508335735707 71 0.46498817551872262
		3 0 0.47254139008916396 63 0.05503929013371732 71 0.47241931977711871
		3 0 0.4600442545106056 63 0.093476762768400543 71 0.44647898272099384
		3 0 0.45709925549403385 63 0.086488134514628834 71 0.45641260999133726
		3 0 0.46903181425505736 63 0.077729456705819489 71 0.4532387290391231
		3 0 0.47038987278938293 63 0.10942244529724121 71 0.42018768191337585
		3 0 0.48320744161616924 63 0.094682232956323525 71 0.42211032542750726
		3 0 0.477149602195996 63 0.062851912805051258 71 0.45999848499895268
		3 0 0.49420920014381409 63 0.079865723848342896 71 0.42592507600784302
		3 0 0.49321736783048431 63 0.10302891351963028 71 0.40375371864988541
		3 0 0.49999236315500195 63 0.067246510576508781 71 0.43276112626848928
		3 0 0.48357366614837821 63 0.050156402398712892 71 0.4662699314529089
		3 0 0.48798351570994564 63 0.040177005526106702 71 0.47183947876394766
		3 0 0.48361944071309027 63 0.032776377362540868 71 0.48360418192436883
		3 0 0.48700694247535686 63 0.025986115049286308 71 0.48700694247535686
		3 0 0.49077592122737929 63 0.018463416334559668 71 0.49076066243806099
		3 0 0.49234760036853886 63 0.015304799262922254 71 0.49234760036853886
		3 0 0.49364461713288121 63 0.012726024523058517 71 0.4936293583440603
		3 0 0.49391927947164116 63 0.012176699845666439 71 0.49390402068269235
		3 0 0.49457541752984363 63 0.010849164940312793 71 0.49457541752984363
		3 0 0.48607613097262714 63 0.011810483036975914 71 0.50211338599039701
		3 0 0.48514534262840103 63 0.01005569591326992 71 0.50479896145832903
		3 0 0.44130617421242052 63 0.011657892737219011 71 0.54703593305036047
		3 0 0.44643321674916264 63 0.013580529963206994 71 0.53998625328763039
		3 0 0.38532082251178384 63 0.015899900761616622 71 0.59877927672659959
		3 0 0.44715036817541354 63 0.015289540018124896 71 0.53756009180646158
		3 0 0.4857099381408278 63 0.013290608376025827 71 0.50099945348314634
		3 0 0.48415350733640228 63 0.015869382709751342 71 0.49997710995384637
		3 0 0.49268329877679495 63 0.014633402446410097 71 0.49268329877679495
		3 0 0.48969253076755853 63 0.020614938464882885 71 0.48969253076755853
		3 0 0.48168155281796182 63 0.021805142861948481 71 0.49651330432008967
		3 0 0.44660105802192102 63 0.018249790911565079 71 0.53514915106651395
		3 0 0.446601066340514 63 0.024933241493502567 71 0.52846569216598338
		3 0 0.39061570895119957 63 0.022201877500896854 71 0.58718241354790357
		3 0 0.38802167484148087 63 0.018066681786874816 71 0.59391164337164426
		3 0 0.32722974128303811 63 0.02671854781656105 71 0.64605171090040092
		3 0 0.33490500228373338 63 0.036362249810571783 71 0.62873274790569489
		3 0 0.26991682641394077 63 0.040482184876154702 71 0.68960098870990449
		3 0 0.284611290034117 63 0.053482872498833996 71 0.66190583746704901
		3 0 0.23314260467460612 63 0.061890596044598428 71 0.70496679928079542
		3 0 0.24545661739324603 63 0.080155639646118285 71 0.67438774296063564
		3 0 0.18498512163713937 63 0.067261772372179396 71 0.74775310599068123
		3 0 0.21988250069451518 63 0.046692605539866476 71 0.73342489376561837
		3 0 0.17726406785220034 63 0.051621270396211567 71 0.77111466175158805
		3 0 0.13756008036255596 63 0.051712824353193514 71 0.81072709528425047
		3 0 0.1691920322864654 63 0.037644006592363166 71 0.79316396112117138
		3 0 0.1370565300325175 63 0.03891050457548538 71 0.82403296539199711
		3 0 0.16163882432536605 63 0.030029754750098048 71 0.80833142092453591
		3 0 0.13037309244831044 63 0.03221179592925006 71 0.83741511162243953
		3 0 0.15130846033273124 63 0.025116350221078654 71 0.82357518944619013
		3 0 0.19430838959608351 63 0.022964828229654465 71 0.78272678217426206
		3 0 0.17924773592922238 63 0.019943540804403605 71 0.80080872326637398
		3 0 0.23959715842900542 63 0.018066682056089356 71 0.74233615951490517
		3 0 0.22838178617331067 63 0.016540780909967138 71 0.75507743291672225
		3 0 0.16792554038596616 63 0.018005647167689664 71 0.81406881244634421
		3 0 0.13585106876658945 63 0.02128633460455014 71 0.84286259662886043
		3 0 0.12610055388789107 63 0.019195848897138153 71 0.8547035972149708
		3 0 0.1056992397831852 63 0.024261844959421242 71 0.87003891525739352
		3 0 0.095201037469502398 63 0.022156100637629253 71 0.88264286189286834
		3 0 0.083939877943772279 63 0.027115280964199576 71 0.88894484109202809
		3 0 0.078278778379659048 63 0.024734874680482556 71 0.89698634693985835
		3 0 0.065491719814171651 63 0.029571983412429999 71 0.90493629677339837
		3 0 0.062333103965965329 63 0.026901655199769756 71 0.91076524083426491
		3 0 0.050675213148164699 63 0.031448844703104925 71 0.91787594214873036
		3 0 0.049729153513908386 63 0.028290227055549622 71 0.92198061943054199
		3 0 0.030777447154949955 63 0.035049975179508142 71 0.93417257766554185
		3 0 0.029297322253117875 63 0.02882429233807543 71 0.94187838540880664
		3 0 0.025116350501775742 63 0.04122987762093544 71 0.93365377187728882
		3 0 0.040222781742600015 63 0.058884563470976869 71 0.90089265478642311
		3 0 0.042313266703163335 63 0.071030743684734193 71 0.88665598961210246
		3 0 0.069611660617503068 63 0.094712748417908332 71 0.83567559096458854
		3 0 0.047486077109611086 63 0.082490271283494843 71 0.8700236516068941
		3 0 0.027222094499612152 63 0.060028991363348619 71 0.91274891413703918
		3 0 0.029144731467271277 63 0.06242465798487911 71 0.90843061054784957
		3 0 0.019043259890176651 63 0.049317160228406196 71 0.9316395798814171
		3 0 0.021393148826243789 63 0.047043566975097179 71 0.93156328419865908
		3 0 0.018585488200187683 63 0.043961241841316223 71 0.93745326995849609
		3 0 0.0236972605906631 63 0.047226670777598984 71 0.92907606863173786
		3 0 0.030304416449658266 63 0.053070875758847676 71 0.91662470779149408
		3 0 0.031616695460801536 63 0.049729153884419453 71 0.91865415065477896
		3 0 0.04573128864213459 63 0.054169529598901818 71 0.90009918175896364
		3 0 0.036423283882005442 63 0.054612039502485853 71 0.90896467661550873
		3 0 0.026688029641627878 63 0.05218585512544776 71 0.92112611523292431
		3 0 0.029663539057545086 63 0.059052416182070494 71 0.91128404476038438
		3 0 0.01925688645349604 63 0.045883879920167472 71 0.93485923362633649
		3 0 0.018921186900793932 63 0.044434271173477362 71 0.93664454192572866
		3 0 0.019974060803072024 63 0.048752577202452213 71 0.93127336199447575
		3 0 0.032150759813923242 63 0.070237277891676456 71 0.89761196229440032
		3 0 0.041412986814975739 63 0.063889525830745697 71 0.89469748735427856
		3 0 0.044678415270924282 63 0.077821007411535692 71 0.87750057731754005
		3 0 0.034164949997030569 63 0.083329520498741261 71 0.88250552950422811
		3 0 0.022125581238184904 63 0.063965819656912573 71 0.91390859910490252
		3 0 0.025604639297741053 63 0.083527885688572695 71 0.89086747501368624
		3 0 0.020370794953443731 63 0.079392695859270251 71 0.90023650918728604
		3 0 0.022644389673818533 63 0.12086671725884136 71 0.85648889306734011
		3 0 0.018371862914244658 63 0.12336919203948023 71 0.85825894504627509
		3 0 0.016968032376781166 63 0.09210345911253888 71 0.89092850851067995
		3 0 0.015228504627036957 63 0.13192950459425254 71 0.85284199077871048
		3 0 0.013977263884894149 63 0.09993133572944686 71 0.88609140038565903
		3 0 0.012146181528750466 63 0.14322118581178661 71 0.84463263265946298
		3 0 0.011139086209052258 63 0.10737773546046772 71 0.88148317833048007
		3 0 0.010116731992955348 63 0.167818729172728 71 0.82206453883431663
		3 0 0.0090180818693237873 63 0.12954909665159184 71 0.8614328214790844
		3 0 0.010193026861944862 63 0.21886015447927998 71 0.77094681865877512
		3 0 0.013778896976674167 63 0.25606164288509331 71 0.73015946013823252
		3 0 0.013382161630952391 63 0.20715647414957658 71 0.77946136421947099
		3 0 0.018402380628852799 63 0.30270847283497582 71 0.67888914653617138
		3 0 0.017883574223668656 63 0.23375294623657614 71 0.74836347953975524
		3 0 0.022919050836882348 63 0.34987410120947432 71 0.62720684795364334
		3 0 0.018326085402184826 63 0.37540245755393908 71 0.60627145704387608
		3 0 0.022690166041517624 63 0.44214541214121966 71 0.53516442181726276
		3 0 0.028717479004687435 63 0.40909436726099224 71 0.5621881537343203
		3 0 0.027542535933843818 63 0.51647211467960774 71 0.45598534938654844
		3 0 0.036011294067074269 63 0.47690547223248292 71 0.48708323370044282
		1 0 0.036377508599804813;
	setAttr ".wl[1607:1773].w"
		2 63 0.34621194391934512 71 0.61741054748085011
		3 0 0.046692604844092454 63 0.39575799267625084 71 0.55754940247965667
		3 0 0.04318303290586583 63 0.24470894312160771 71 0.71210802397252648
		3 0 0.057267110154772809 63 0.27879759357723305 71 0.66393529626799419
		3 0 0.051468680968858142 63 0.16775768807801208 71 0.78077363095312979
		3 0 0.03819333016872406 63 0.14517433941364288 71 0.81663233041763306
		3 0 0.032990004007033898 63 0.21484702265288994 71 0.7521629733400762
		3 0 0.02848859227391692 63 0.12558175225762691 71 0.84592965546845622
		3 0 0.025803004794133728 63 0.19429312248299951 71 0.77990387272286676
		3 0 0.028274968687816988 63 0.29828337279384393 71 0.67344165851833904
		3 0 0.022262911994797231 63 0.25889983483888396 71 0.71883725316631886
		3 0 0.020691235157991372 63 0.18056001239985259 71 0.79874875244215604
		3 0 0.016876477685285815 63 0.17848478191165335 71 0.80463874040306083
		3 0 0.013992522986529164 63 0.17689784052397706 71 0.80910963648949374
		3 0 0.035797667691795806 63 0.099198902749986648 71 0.86500342955821752
		3 0 0.04910353180355008 63 0.11532768564176676 71 0.83556878255468314
		3 0 0.047669184350765947 63 0.095780881043167426 71 0.85654993460606665
		3 0 0.065751127898693085 63 0.10614175349473953 71 0.82810711860656738
		3 0 0.06224155169430285 63 0.08480964759010165 71 0.85294880071559553
		3 0 0.086411839282248035 63 0.090974284165182315 71 0.82261387655256968
		3 0 0.081101699455057089 63 0.072175173876059442 71 0.8467231266688835
		3 0 0.11619745281485805 63 0.094316013860076764 71 0.78948653332506513
		3 0 0.089265277476639801 63 0.11515983681768543 71 0.79557488570567481
		3 0 0.090043483822889861 63 0.14190889683501576 71 0.76804761934209442
		3 0 0.066834515329423944 63 0.13026626116932344 71 0.80289922350125265
		3 0 0.069535359740257263 63 0.18864728510379791 71 0.74181735515594482
		3 0 0.093675135170293813 63 0.20436407321149003 71 0.70196079161821612
		3 0 0.076066223500185506 63 0.30836956774087049 71 0.61556420875894402
		3 0 0.059845884068077997 63 0.44170290725346179 71 0.49845120867846021
		3 0 0.077409022133119565 63 0.4769054686792602 71 0.44568550918762018
		3 0 0.056443121494513457 63 0.59803158267599188 71 0.34552529582949465
		3 0 0.044983595609664917 63 0.54346531629562378 71 0.4115510880947113
		3 0 0.040466927293441646 63 0.66547644634154768 71 0.29405662636501062
		3 0 0.050598915854837431 63 0.71151292589125381 71 0.23788815825390874
		3 0 0.06581216256460426 63 0.73374533106576412 71 0.20044250636963168
		3 0 0.072266725532212098 63 0.63173876310173382 71 0.29599451136605409
		3 0 0.088349735252192571 63 0.73327229768174218 71 0.17837796706606521
		3 0 0.094621194979232631 63 0.64405279391925341 71 0.26132601110151393
		3 0 0.10165560245513916 63 0.49584192037582397 71 0.40250247716903687
		3 0 0.1262531410716006 63 0.63526361234093287 71 0.2384832465874665
		3 0 0.12080567420129235 63 0.71491569813278089 71 0.16427862766592671
		3 0 0.16490424923741445 63 0.67856871070610425 71 0.15652704005648135
		3 0 0.17006179436949201 63 0.6041504650689592 71 0.22578774056154877
		3 0 0.13492026925086975 63 0.49515527486801147 71 0.36992445588111877
		3 0 0.17898832528275735 63 0.47339589109116631 71 0.34761578362607631
		3 0 0.2273746911790176 63 0.55165941345184166 71 0.22096589536914074
		3 0 0.22162203820976673 63 0.62584877946747508 71 0.15252918232275817
		3 0 0.28847182226884099 63 0.56028074860991162 71 0.15124742912124736
		3 0 0.29613184928894043 63 0.48332950472831726 71 0.22053864598274231
		3 0 0.2351262683402558 63 0.43134202910450059 71 0.33353170255524361
		3 0 0.35771724581718445 63 0.4915083646774292 71 0.15077438950538635
		3 0 0.17795071005821228 63 0.32570382952690125 71 0.49634546041488647
		3 0 0.21228350382620836 63 0.20335697824721072 71 0.58435951792658092
		3 0 0.13508811593055725 63 0.3337911069393158 71 0.53112077713012695
		3 0 0.10131990909576416 63 0.32762646675109863 71 0.57105362415313721
		3 0 0.033295185366129437 63 0.59552909718540603 71 0.37117571744846456
		3 0 0.05812161285903425 63 0.068406192919473502 71 0.87347219422149225
		3 0 0.051529716892278629 63 0.057724878406989866 71 0.89074540470073149
		3 0 0.065369648773382638 63 0.057648582528573793 71 0.87698176869804356
		3 0 0.045838101673764696 63 0.061005568630868895 71 0.8931563296953664
		3 0 0.073334855635915533 63 0.088685435393886708 71 0.8379797089701978
		3 0 0.047760739566678256 63 0.077729455547560333 71 0.87450980488576135
		3 0 0.074494548696983964 63 0.096559093121879491 71 0.82894635818113649
		3 0 0.10884260224040446 63 0.10305943186492575 71 0.78809796589466985
		3 0 0.10757610362136519 63 0.11042954192205581 71 0.78199435445657905
		3 0 0.064072630822117393 63 0.076981767438487947 71 0.8589456017393946
		3 0 0.098863201562982839 63 0.091264212681298237 71 0.80987258575571897
		3 0 0.15362783234202362 63 0.11404593628781844 71 0.73232623137015795
		3 0 0.15228504169412019 63 0.10437171316700747 71 0.74334324513887229
		3 0 0.20355535311830614 63 0.10325780150509631 71 0.69318684537659758
		3 0 0.20842297996351064 63 0.11436637086768063 71 0.67721064916880869
		3 0 0.26085298864762502 63 0.098603798469844489 71 0.64054321288253047
		3 0 0.25243000136427585 63 0.089509423431360105 71 0.65806057520436401
		3 0 0.3105821265193503 63 0.08117799339923272 71 0.60823988008141694
		3 0 0.31856260415679077 63 0.090150306153676793 71 0.59128708968953247
		3 0 0.36559089745885953 63 0.07261768674390251 71 0.5617914157972379
		3 0 0.3985961586550737 63 0.04448004712581529 71 0.55692379421911109
		3 0 0.41710538293578303 63 0.065445945642083073 71 0.51744867142213391
		3 0 0.45537499102251594 63 0.061753262524529499 71 0.48287174645295455
		3 0 0.45557335019111633 63 0.070481419563293457 71 0.47394523024559021
		3 0 0.4764171838760376 63 0.070298314094543457 71 0.45328450202941895
		3 0 0.46248570084571838 63 0.084153503179550171 71 0.45336079597473145
		3 0 0.4273594351661163 63 0.085481040816612841 71 0.48715952401727081
		3 0 0.43372243642807007 63 0.07631036639213562 71 0.48996719717979431
		3 0 0.3804684437636866 63 0.082322423073559137 71 0.53720913316275432
		3 0 0.42555886189968239 63 0.059189743852691767 71 0.51525139424762578
		3 0 0.47359425535193467 63 0.073411152860688458 71 0.45299459178737689
		3 0 0.47203785005197729 63 0.054825667087638127 71 0.47313648286038457
		3 0 0.45561913674218513 63 0.03559929957090243 71 0.50878156368691241
		3 0 0.48496222857357729 63 0.032639049236767359 71 0.48239872218965529
		3 0 0.40845348974555556 63 0.041840236166414961 71 0.54970627408802952
		3 0 0.39627679222897011 63 0.030899518352572361 71 0.57282368941845752
		3 0 0.34799724557997846 63 0.047257192080786881 71 0.6047455623392346
		3 0 0.36662851944651037 63 0.063813230459096343 71 0.56955825009439331
		3 0 0.30251011477790857 63 0.071854733466019727 71 0.62563515175607165
		3 0 0.32181278350670312 63 0.090669111768441071 71 0.58751810472485577
		3 0 0.26009002715483348 63 0.098664836565626218 71 0.64124513627954027
		3 0 0.32813001167967931 63 0.10074006171137187 71 0.57112992660894879
		3 0 0.38118562386323229 63 0.091432058002293537 71 0.52738231813447412
		3 0 0.3712825262088148 63 0.080750742869468248 71 0.54796673092171688
		3 0 0.2687113881111145 63 0.10959029197692871 71 0.62169831991195679
		3 0 0.41953154773218115 63 0.073441668250535899 71 0.50702678401728296
		3 0 0.19958800077438354 63 0.10170137882232666 71 0.69871062040328979
		3 0 0.19087509526498475 63 0.083955137670708627 71 0.72516976706430658
		3 0 0.13894865330900708 63 0.081788363510023457 71 0.77926298318096943
		3 0 0.13716334206732617 63 0.065995269015396152 71 0.79684138891727763
		3 0 0.097215229231346095 63 0.058197908970682458 71 0.84458686179797149
		3 0 0.10527199585193392 63 0.046326391744065221 71 0.8484016124040008
		3 0 0.085023269374010224 63 0.039719235299971831 71 0.87525749532601793
		3 0 0.10542458452917017 63 0.03419546833925647 71 0.8603799471315734
		3 0 0.093781949137694567 63 0.030533302916586059 71 0.87568474794571938
		3 0 0.11902037528947834 63 0.027832456555197907 71 0.85314716815532377
		3 0 0.11639581794136492 63 0.038956285103504136 71 0.84464789695513098
		3 0 0.073136491656469405 63 0.034012357748722639 71 0.89285115059480791
		3 0 0.071824214014705012 63 0.046677346403201175 71 0.88149843958209384
		3 0 0.057633324169367756 63 0.03749141758326998 71 0.90487525824736226
		3 0 0.062897691515019283 63 0.064103150788043461 71 0.87299915769693726
		3 0 0.095521480556737481 63 0.075638972786359282 71 0.82883954665690318
		3 0 0.14428931152173927 63 0.099061568847412573 71 0.75664911963084813
		3 0 0.041840236322281982 63 0.048630501712631419 71 0.90952926196508654
		3 0 0.49762722293704126 63 0.053391318171568385 71 0.44898145889139035
		3 0 0.49065384999891892 63 0.032120243193510818 71 0.47722590680757027
		3 0 0.50222019657499428 63 0.054840924242256887 71 0.44293887918274882
		3 0 0.48993667230104399 63 0.034271761264327745 71 0.47579156643462828
		3 0 0.48908216945467181 63 0.02183566109065636 71 0.48908216945467181
		3 0 0.5020828674780361 63 0.05883878644723789 71 0.43907834607472601
		3 0 0.50043487548828125 63 0.080064088106155396 71 0.41950103640556335
		3 0 0.49863430857658386 63 0.089707791805267334 71 0.4116578996181488
		3 0 0.48589304089546204 63 0.091950863599777222 71 0.42215609550476074
		3 0 0.48636606698010909 63 0.08722057258502075 71 0.4264133604348701
		3 0 0.48039978742599487 63 0.072053104639053345 71 0.44754710793495178
		3 0 0.48018616080145415 63 0.076600290264187076 71 0.44321354893435871
		3 0 0.48165103434286238 63 0.062973983116641763 71 0.4553749825404958
		3 0 0.47759213331949513 63 0.061402305045689567 71 0.46100556163481532
		3 0 0.48390936130420326 63 0.10249484922744559 71 0.41359578946835118
		3 0 0.47914854763035208 63 0.11578545978185817 71 0.40506599258778975
		3 0 0.48303959493398063 63 0.11808957335486372 71 0.39887083171115567
		3 0 0.48245974656254431 63 0.084870679901977178 71 0.43266957353547852
		3 0 0.49643702054674954 63 0.073258564967789722 71 0.43030441448546075
		3 0 0.50061799214671532 63 0.074937054699742531 71 0.42444495315354214
		3 0 0.1965056777521122 63 0.093965052158161227 71 0.70952927008972655
		3 0 0.013519494291080913 63 0.30901045585643083 71 0.67747004985248827
		3 0 0.0098420685857643717 63 0.24594490964321231 71 0.74421302177102333
		3 0 0.021667812019586563 63 0.056412603706121445 71 0.92191958427429199
		3 0 0.01617456368614276 63 0.044251161322430857 71 0.93957427499142643
		3 0 0.016556039082496483 63 0.043503469746482303 71 0.93994049117102119
		3 0 0.012771801127414596 63 0.03779659803341124 71 0.94943160083917422
		3 0 0.015259021921565797 63 0.031525138824293648 71 0.95321583925414055
		3 0 0.024597544864501112 63 0.047760741167981881 71 0.92764171396751705
		3 0 0.018356602638959885 63 0.02861066535115242 71 0.9530327320098877
		3 0 0.012420844518036479 63 0.029343098948581125 71 0.9582360565333824
		3 0 0.0094758521774849901 63 0.030930036073987598 71 0.95959411174852738
		3 0 0.010009918473771794 63 0.036057070300620837 71 0.95393301122560736
		3 0 0.0081177997907979377 63 0.033722438514909088 71 0.95815976169429296
		3 0 0.0081940946001009506 63 0.034241244515788222 71 0.95756466088411085
		3 0 0.010803387691513044 63 0.038757917225733796 71 0.95043869508275314
		3 0 0.0082398718299715526 63 0.034622721406279804 71 0.9571374067637487
		3 0 0.29571982777536171 63 0.014663919587970978 71 0.68961625263666726
		3 0 0.30647746413523252 63 0.016113527479325103 71 0.67740900838544238
		3 0 0.36301212995761822 63 0.012603952373322765 71 0.62438391766905899
		3 0 0.37730982723967255 63 0.01397726398903288 71 0.60871290877129458
		3 0 0.42865642386252667 63 0.010543984233334851 71 0.56079959190413853
		3 0 0.31557183164622582 63 0.018265049156116171 71 0.66616311919765803
		3 0 0.24945448338985443 63 0.020553901791572571 71 0.729991614818573
		3 0 0.25632104755045937 63 0.024170291128946302 71 0.71950866132059432
		3 0 0.20160219786770969 63 0.026947434082629621 71 0.77145036804966072
		3 0 0.20743114297098666 63 0.033539329598752061 71 0.75902952743026131;
	setAttr ".wl[1774:1853].w"
		3 0 0.2607003733849132 63 0.029663538394513324 71 0.70963608822057345
		3 0 0.32100404385118336 63 0.021255817976975299 71 0.6577401381718414
		3 0 0.48072021214678451 63 0.0091706717370499125 71 0.51010911611616561
		3 0 0.49539940488134854 63 0.0092164490260385652 71 0.49538414609261289
		3 0 0.49567406723328222 63 0.0086671243222991561 71 0.49565880844441867
		3 0 0.49524681468781939 63 0.0095063706243612087 71 0.49524681468781939
		3 0 0.49430075517995636 63 0.011398489640087307 71 0.49430075517995636
		3 0 0.49318684703782922 63 0.013626305924341563 71 0.49318684703782922
		3 0 0.49228656429504947 63 0.015426871409901059 71 0.49228656429504947
		3 0 0.49027237387424777 63 0.019455252251504459 71 0.49027237387424777
		3 0 0.48853284484545023 63 0.022934310309099482 71 0.48853284484545023
		3 0 0.48503852884364096 63 0.02992294231271812 71 0.48503852884364096
		3 0 0.47895017979964882 63 0.042099640400702361 71 0.47895017979964882
		3 0 0.49433127321860532 63 0.011337453562789337 71 0.49433127321860532
		3 0 0.49576562135161661 63 0.0084840160856729588 71 0.49575036256271043
		3 0 0.49494163400352231 63 0.010116731992955348 71 0.49494163400352231
		3 0 0.46573586659836369 63 0.068528266803272564 71 0.46573586659836369
		3 0 0.48657969002857571 63 0.026840619942848531 71 0.48657969002857571
		3 0 0.48075074315630451 63 0.038498513687390934 71 0.48075074315630451
		3 0 0.48195620653098514 63 0.036087586938029721 71 0.48195620653098514
		3 0 0.47522697737863245 63 0.049546045242735093 71 0.47522697737863245
		3 0 0.46744487734388285 63 0.065110245312234277 71 0.46744487734388285
		3 0 0.46883344824922624 63 0.062348362290666856 71 0.46881818946010689
		3 0 0.46248569395414452 63 0.075043870880546107 71 0.46247043516530939
		3 0 0.45714503526687622 63 0.085709929466247559 71 0.45714503526687622
		3 0 0.45081254504015633 63 0.098374909919687281 71 0.45081254504015633
		3 0 0.46070038929059809 63 0.078599221418803766 71 0.46070038929059809
		3 0 0.44550240371750593 63 0.10901045135416426 71 0.44548714492832975
		3 0 0.45828946400531834 63 0.083421071989363313 71 0.45828946400531834
		3 0 0.46881818946010689 63 0.0623636210797862 71 0.46881818946010689
		3 0 0.47618829671828117 63 0.047638665352329627 71 0.4761730379293892
		3 0 0.43442435367179971 63 0.13115129265640058 71 0.43442435367179971
		3 0 0.44168764681881401 63 0.11662470636237193 71 0.44168764681881401
		3 0 0.42471960819839849 63 0.15173571037852332 71 0.42354468142307822
		3 0 0.43219652771949768 63 0.13704127073287964 71 0.43076220154762268
		3 0 0.41835660365755267 63 0.17093156532841272 71 0.41071183101403463
		3 0 0.42546731233596802 63 0.1584954559803009 71 0.41603723168373108
		3 0 0.43387503078393685 63 0.14370946800275844 71 0.42241550121330473
		3 0 0.42711529135704041 63 0.17225909233093262 71 0.40062561631202698
		3 0 0.43662165944842013 63 0.15881590308523322 71 0.40456243746634668
		3 0 0.43244066834449768 63 0.18152132630348206 71 0.38603800535202026
		3 0 0.44432745045911448 63 0.16658275077615306 71 0.38908979876473249
		3 0 0.43979553043537634 63 0.17318989594563686 71 0.38701457361898683
		3 0 0.45015640408266794 63 0.15854123707238546 71 0.39130235884494657
		3 0 0.44922560453414917 63 0.13842985033988953 71 0.4123445451259613
		3 0 0.45946441127652848 63 0.12359807916577337 71 0.41693750955769815
		3 0 0.46007477894369675 63 0.11389333669920759 71 0.4260318843570956
		3 0 0.4682841335854242 63 0.099137865745558329 71 0.43257800066901742
		3 0 0.47058823704719543 63 0.072449833154678345 71 0.45696192979812622
		3 0 0.46207371354103088 63 0.087739378213882446 71 0.45018690824508667
		3 0 0.47174792778867591 63 0.059540703005482212 71 0.46871136920584189
		3 0 0.47818723142822372 63 0.047028306696458508 71 0.47478446187531775
		3 0 0.47803464888062064 63 0.04449530724060019 71 0.47747004387877912
		3 0 0.48244449136820067 63 0.037628747242474947 71 0.47992676138932433
		3 0 0.48023193716830059 63 0.039597160819194011 71 0.48017090201250534
		3 0 0.47504387190647185 63 0.053360802184060259 71 0.4715953259094679
		3 0 0.47562371798560549 63 0.049942779355816924 71 0.47443350265857759
		3 0 0.47170215845108032 63 0.048935681581497192 71 0.47936215996742249
		3 0 0.47867550910999429 63 0.059403370401970627 71 0.46192112048803508
		3 0 0.4838025533869672 63 0.049347675969096449 71 0.46684977064393629
		3 0 0.44972914457321167 63 0.12886244058609009 71 0.42140841484069824
		3 0 0.44115357933709654 63 0.15323109696461115 71 0.40561532369829234
		3 0 0.43176928805961146 63 0.16723887871561763 71 0.40099183322477094
		3 0 0.42978560924530029 63 0.18568703532218933 71 0.38452735543251038
		3 0 0.41879910230636597 63 0.19736018776893616 71 0.38384070992469788
		3 0 0.41112381219863892 63 0.2065461277961731 71 0.38233006000518799
		3 0 0.41414510586641573 63 0.20187686082904249 71 0.38397803330454183
		3 0 0.41110855953557135 63 0.20593576440119393 71 0.38295567606323477
		3 0 0.41355001926422119 63 0.19180589914321899 71 0.39464408159255981
		3 0 0.41904326024522603 63 0.18347447563783897 71 0.39748226411693499
		3 0 0.42206454277038574 63 0.19296559691429138 71 0.38496986031532288
		3 0 0.40471502233933609 63 0.054108491820652221 71 0.54117648584001166
		3 0 0.35112535430304176 63 0.05963225573849297 71 0.58924238995846523
		3 0 0.3600366249694163 63 0.083680476385372737 71 0.55628289864521097
		3 0 0.2953078404768133 63 0.065232320647950162 71 0.6394598388752365
		3 0 0.24159609321347086 63 0.070054167584795532 71 0.68834973920173359
		3 0 0.17888151575688499 63 0.061814298602566459 71 0.75930418564054858
		3 0 0.1923094526506256 63 0.073579005348838822 71 0.73411154200053552
		3 0 0.13579003512859344 63 0.0635996013879776 71 0.80061036348342896
		3 0 0.46378269791603088 63 0.28068971633911133 71 0.25552758574485779;
	setAttr -s 79 ".pm";
	setAttr ".pm[0]" -type "matrix" 0 -0 -1 -0 0.99799027986901856 -0.063367194090933054 -0 0
		 -0.063367194090933054 -0.99799027986901867 -0 0 -95.559524140488392 8.3529922361861715 -3.4314998759166221e-17 1;
	setAttr ".pm[1]" -type "matrix" 0 -0 -1 -0 0.98220797016103401 0.18779644126591369 -0 -0
		 0.18779644126591374 -0.98220797016103401 0 -0 -98.179537472967525 -16.686798167121658 4.3202194641745812e-16 1;
	setAttr ".pm[2]" -type "matrix" 0 -0 -1 -0 0.99176140629857179 0.12809884065314414 -0 -0
		 0.1280988406531442 -0.99176140629857179 0 -0 -105.79112581470955 -10.312733827340182 2.4642770704620008e-16 1;
	setAttr ".pm[3]" -type "matrix" 0 -0 -1 -0 0.99804167658749499 -0.062552472328609804 -0 0
		 -0.062552472328609748 -0.99804167658749499 0 0 -112.93116808215187 11.337483986926584 1.2350709678255032e-16 1;
	setAttr ".pm[4]" -type "matrix" 0 -7.8457562571503513e-06 -0.99999999996922206 -0
		 0.98641974755132822 -0.16424396987138712 1.2886181543573101e-06 0 -0.16424396987644216 -0.98641974752096839 7.7392089065275019e-06 0
		 -119.65995581271704 23.693152323860112 -0.00018589069810239194 1;
	setAttr ".pm[5]" -type "matrix" -1.8369095133075878e-13 1.5897534116537124e-11 -1 -0
		 0.98439676970875678 -0.17596306370077874 -2.9782035882479106e-12 0 -0.17596306370077869 -0.984396769708757 -1.5617158413075801e-11 0
		 -138.80815577827528 25.345680206388408 4.2901809001282565e-10 1;
	setAttr ".pm[6]" -type "matrix" -6.6158600073637137e-12 1.4456684603152542e-11 -1 -0
		 0.97116051578906692 0.23842661884175731 -2.9782035882479102e-12 -0 0.23842661884175742 -0.97116051578906704 -1.5617158413075794e-11 -0
		 -148.02413413726134 -37.954183218738514 4.2901649057184837e-10 1;
	setAttr ".pm[7]" -type "matrix" -6.1294451675869628e-12 1.7098227304699728e-06 -0.99999999999853828 -0
		 0.97858030038111177 0.20586547963631138 3.5198747834748905e-07 -0 0.20586547963661239 -0.97858030037968147 -1.6732001030229328e-06 -0
		 -154.31633419745555 -32.819682332318422 -5.6114928351548255e-05 1;
	setAttr ".pm[8]" -type "matrix" 2.0731685376878032e-14 -5.2736972103718422e-13 -1 -0
		 0.99999999999999956 -2.7642915900707262e-08 2.0731699180479388e-14 0 -2.7642915845119117e-08 -0.99999999999999922 5.2736971586760892e-13 0
		 -162.57510095546689 0.6631271895736045 -6.9220508941227083e-11 1;
	setAttr ".pm[9]" -type "matrix" 0.98722325285369872 -0.045885930500282487 0.15259334981277803 -0
		 -0.15258975017460899 0.0036018072449419116 0.98828305415312145 0 -0.045897899370362635 -0.99894019258747058 -0.0034459348070639737 -0
		 20.834526686610335 -2.1993972353802893 -144.81073304490477 1;
	setAttr ".pm[10]" -type "matrix" 0.57603356970603825 -0.032592100671480384 0.81677602899787582 -0
		 -0.81709064454000069 -0.051578494511193576 0.57419729841681266 0 0.023413781773248543 -0.99813697150129566 -0.05634164485791858 -0
		 106.43028049579613 5.4729235446178173 -98.116150068235385 1;
	setAttr ".pm[11]" -type "matrix" 0.46829763500528526 0.33700777958812422 0.81677602899787605 -0
		 -0.60274413765566648 -0.55407307010227613 0.57419729841681277 0 0.64606255855774775 -0.76120220013116147 -0.056341644857918607 -0
		 57.705277019372737 53.733736277159572 -98.116150068235285 1;
	setAttr ".pm[12]" -type "matrix" 0.50409945495245101 0.33849062611899494 0.79454882514934999 -0
		 -0.60398945624054445 -0.51942160302091689 0.60448154236951968 0 0.61731716019149518 -0.78461792889581095 -0.057395377761239361 -0
		 47.473584484677097 49.768920692360659 -100.73462759546058 1;
	setAttr ".pm[13]" -type "matrix" 0.50409934937943979 0.33849062722902823 0.79454889165697262 -0
		 -0.6039895354012087 -0.51942160364797818 0.60448146273446202 0 0.61731716895049649 -0.78461792800181462 -0.057395295774846596 -0
		 38.39948766307743 50.089752883142609 -100.46807637246528 1;
	setAttr ".pm[14]" -type "matrix" 0.45776606561811328 -0.64550904437145162 0.61136593199422551 -0
		 -0.63486683690404511 -0.71872771411568359 -0.28350409584606834 0 0.62241009677540171 -0.25835740089399173 -0.73882144313449372 -0
		 34.684346122405991 109.9739843467096 12.011274326347484 1;
	setAttr ".pm[15]" -type "matrix" 0.48489773769626671 -0.67018644860059917 0.56189350244433245 -0
		 -0.60591821332048457 -0.72073617183479421 -0.33675286097587714 0 0.63066417588408663 -0.17717080662751039 -0.75556151472623567 -0
		 26.831433812930602 110.68854436359625 20.436040249929938 1;
	setAttr ".pm[16]" -type "matrix" 0.062225503872753163 -0.82486585489922115 0.56189350244433234 -0
		 -0.89359104695641289 -0.29680389388264899 -0.33675286097587698 0 0.44454811603146255 -0.48114838667242121 -0.75556151472623534 -0
		 75.618504547712334 83.448560433435006 20.436040249929921 1;
	setAttr ".pm[17]" -type "matrix" -0.23431932551154891 -0.79332852312434454 0.56189350244433212 0
		 -0.94077026842430067 0.03935495741872172 -0.33675286097587692 0 0.24504235499333674 -0.60752040436837662 -0.75556151472623523 -0
		 95.462679462783328 53.044054692818136 20.436040249929874 1;
	setAttr ".pm[18]" -type "matrix" -0.36851954040065693 -0.74058695657817897 0.56189350244433245 0
		 -0.91964393761217333 0.20212010943430922 -0.33675286097587703 0 0.13582480022464327 -0.6408419626620373 -0.75556151472623545 -0
		 100.78697591503283 36.09088162744461 20.436040249929874 1;
	setAttr ".pm[19]" -type "matrix" 0.50165929984922586 -0.86150484141863237 0.078405070544201108 -0
		 -0.81946977563034784 -0.50229885137241892 -0.27598034484052603 0 0.27714118009262162 0.074197520997709002 -0.95796006919634413 -0
		 53.495590922837458 93.883233434698852 39.527703497094578 1;
	setAttr ".pm[20]" -type "matrix" 0.26354050175138494 -0.93037057822145774 0.25486661436229341 -0
		 -0.91778928814692895 -0.32317414573818043 -0.23069740806768926 0 0.29700038131184336 -0.17311573789308352 -0.93905362721963481 -0
		 70.569005181413004 84.524479688125552 25.509234300609666 1;
	setAttr ".pm[21]" -type "matrix" -0.092201469831926147 -0.96257046383334111 0.25486661436229335 0
		 -0.97249693640637469 0.032068903802027635 -0.23069740806768926 0 0.21388921815053188 -0.26912764176985104 -0.93905362721963481 -0
		 92.884441063882775 54.52368272214644 25.509234300609606 1;
	setAttr ".pm[22]" -type "matrix" -0.17436652109979217 -0.95112529416636626 0.25486661436229341 0
		 -0.96616935149144256 0.1153060716070639 -0.23069740806768926 0 0.19003447202589024 -0.28647021598673789 -0.93905362721963481 -0
		 95.183488685287372 46.536522629255515 25.509234300609588 1;
	setAttr ".pm[23]" -type "matrix" 0.59060503118117336 -0.73083333884862656 0.34215249227625594 -0
		 -0.65963271076520436 -0.68147046384688714 -0.31699005314497958 0 0.46483371653961686 -0.03847905575344418 -0.8845614609716449 -0
		 29.859978948116556 107.22853509030105 30.39530525378953 1;
	setAttr ".pm[24]" -type "matrix" 0.1562381940841959 -0.88283473502988563 0.44293617749515585 -0
		 -0.90993079452509795 -0.30308700145347256 -0.28313286408480803 0 0.38420772491483385 -0.35880510054157982 -0.85067227763758335 -0
		 73.837837134590927 84.41352968000156 20.992614199752783 1;
	setAttr ".pm[25]" -type "matrix" -0.13914028536722983 -0.88569042201770753 0.44293617749515563 0
		 -0.95903783110600815 0.0090675124822773168 -0.28313286408480792 0 0.24675173656006633 -0.46418773848894085 -0.85067227763758302 -0
		 92.555475994070321 57.453831159040327 20.992614199752879 1;
	setAttr ".pm[26]" -type "matrix" -0.2784797358133736 -0.85220688767886221 0.44293617749515568 0
		 -0.94534178719106654 0.1617550205265135 -0.28313286408480798 0 0.16964062641865221 -0.49757284283527065 -0.85067227763758313 -0
		 98.291161330797465 42.333914954640612 20.992614199752715 1;
	setAttr ".pm[27]" -type "matrix" -0.23677732947120234 0.3580451068080544 0.90318336883453276 -0
		 -0.46744570505554672 -0.85693276787306782 0.21716524623089359 0 0.85172237793403516 -0.3707693795827951 0.37026889970693028 -0
		 43.319619360309311 78.534900135551482 -70.958618846610079 1;
	setAttr ".pm[28]" -type "matrix" -0.045744985004837348 0.47737462531297914 0.87750832671502355 -0
		 -0.75995290887963407 -0.58677024939719302 0.27959300904660833 0 0.6483663876484409 -0.65407502744688761 0.38962403139188329 -0
		 64.345843526109718 52.176126644376552 -76.528230690124133 1;
	setAttr ".pm[29]" -type "matrix" 0.037845217613481696 0.47806576540219692 0.87750832671502388 -0
		 -0.85029910087978788 -0.44589145353469845 0.2795930090466085 0 0.52493730915873293 -0.75672579949088858 0.38962403139188334 -0
		 69.389458175496756 40.745793878274462 -76.528230690124218 1;
	setAttr ".pm[30]" -type "matrix" 0.38282471691666747 -0.60140250132809647 0.70125620675611999 -0
		 -0.58595958989602781 -0.74492304281921062 -0.31896868072876322 0 0.71421046976822689 -0.28879870441758798 -0.63757251603262433 -0
		 27.99023961814401 111.53927736274952 11.729791100091541 1;
	setAttr ".pm[31]" -type "matrix" 0.1128251535879628 -0.70392486616390404 0.70125620675611988 -0
		 -0.83339914156516925 -0.4513367385363074 -0.31896868072876322 0 0.54103267512812081 -0.54843863033482421 -0.63757251603262433 -0
		 64.530787868163245 93.574290195810747 11.488915408916094 1;
	setAttr ".pm[32]" -type "matrix" -0.071878640933652316 -0.70927652820571274 0.70125620675612022 0
		 -0.9214016860641987 -0.22198629154117586 -0.31896868072876333 0 0.38190626323167609 -0.66906568653925647 -0.63757251603262455 -0
		 82.46950047678385 74.89477311445232 11.488915408916181 1;
	setAttr ".pm[33]" -type "matrix" -0.22388412434001725 -0.6768423977223369 0.70125620675611988 0
		 -0.94761232662415806 -0.017025250192036354 -0.31896868072876322 0 0.22783058903152723 -0.73593104942064824 -0.63757251603262433 -0
		 94.207329612463568 55.804497211239173 11.488915408916206 1;
	setAttr ".pm[34]" -type "matrix" 0.60649254765415761 -0.029307966917277328 0.79454882336779309 -0
		 -0.79463176670251312 -0.056235375135710391 0.60448154473944782 0 0.026965626030396646 -0.99798728732310105 -0.057395377464279113 -0
		 93.385259004106871 6.0267579735113301 -101.69680888390984 1;
	setAttr ".pm[35]" -type "matrix" 0.57603356970603792 -0.032592100671480384 0.81677602899787549 -0
		 -0.81709064454000024 -0.051578494511193569 0.57419729841681255 0 0.023413781773248536 -0.99813697150129577 -0.056341644857918552 -0
		 87.916189004096807 5.4729235446178093 -98.116150068235257 1;
	setAttr ".pm[36]" -type "matrix" 0.98722325285135626 -0.045885930531461817 0.15259334981855666 -0
		 0.15258975018048893 -0.0036018072452173393 -0.98828305415221207 0 0.04589789940119781 0.99894019258603728 0.0034459348118278778 -0
		 -20.834547706916286 2.1994343628065227 144.81067317362968 1;
	setAttr ".pm[37]" -type "matrix" 0.57603356970190278 -0.032592100702963533 0.81677602899953605 -0
		 0.81709064454343117 0.051578494510997296 -0.57419729841194778 0 -0.023413781755254815 0.99813697150027758 0.056341644883428618 -0
		 -106.42986716562406 -5.4728614336200669 98.115865171166732 1;
	setAttr ".pm[38]" -type "matrix" 0.46829763502187433 0.33700777956104855 0.81677602899953594 -0
		 0.60274413765845702 0.55407307010428153 -0.57419729841194778 0 -0.64606255854311956 0.76120220014168849 0.056341644883428604 -0
		 -57.705340251771261 -53.733707545047949 98.115865171166647 1;
	setAttr ".pm[39]" -type "matrix" 0.50409945496813513 0.33849062609139419 0.79454882515115732 -0
		 0.60398945624354849 0.51942160302293072 -0.60448154236478668 0 -0.61731716017574878 0.78461792890638449 0.057395377786054892 -0
		 -47.473684776586033 -49.768895097327757 100.73434494823337 1;
	setAttr ".pm[40]" -type "matrix" 0.50409934939512391 0.3384906272014277 0.79454889165878018 -0
		 0.60398953540421285 0.51942160364999235 -0.60448146272972936 0 -0.61731716893474997 0.78461792801238839 0.057395295799662009 -0
		 -38.399636541036216 -50.089725570257912 100.46779515240362 1;
	setAttr ".pm[41]" -type "matrix" 0.45776606563377215 -0.64550904438380219 0.61136593196945999 -0
		 0.63486683690677292 0.71872771411183767 0.28350409584970848 0 -0.62241009676110248 0.2583574008738313 0.73882144315358966 -0
		 -34.684463937345598 -109.97370532720171 -12.011352937634847 1;
	setAttr ".pm[42]" -type "matrix" 0.48489773771235584 -0.67018644861042576 0.56189350241872726 -0
		 0.60591821332337403 0.72073617183080185 0.3367528609792223 0 -0.63066417586893997 0.17717080660657952 0.7555615147437863 -0
		 -26.831578690188984 -110.68870264748128 -20.436071565158709 1;
	setAttr ".pm[43]" -type "matrix" 0.062225503881315924 -0.82486585491601716 0.56189350241872715 -0
		 0.8935910469567846 0.29680389387773493 0.33675286097922219 0 -0.44454811602951722 0.48114838664665804 0.75556151474378597 -0
		 -75.618512350651898 -83.448596053775717 -20.43607299554056 1;
	setAttr ".pm[44]" -type "matrix" -0.23431932550949855 -0.79332852314308511 0.56189350241872682 -0
		 0.94077026842290523 -0.039354957423448404 0.33675286097922208 -0 -0.24504235500065333 0.60752040434359766 0.75556151474378563 -0
		 -95.46267995502707 -53.044009781515676 -20.436035949871407 1;
	setAttr ".pm[45]" -type "matrix" -0.36851954040189222 -0.74058695659699125 0.56189350241872693 -0
		 0.91964393760997865 -0.20212010943872191 0.33675286097922214 -0 -0.13582480023615154 0.64084196263890547 0.75556151474378552 -0
		 -100.78693029527457 -36.090890550801703 -20.436070334886573 1;
	setAttr ".pm[46]" -type "matrix" 0.50165929985300117 -0.86150484141930661 0.078405070512635913 -0
		 0.81946977563333656 0.50229885136728747 0.27598034484099093 -0 -0.27714118007695088 -0.074197521024616214 0.95796006919879351 -0
		 -53.495341000175429 -93.883047175076555 -39.527588871886962 1;
	setAttr ".pm[47]" -type "matrix" 0.263540501755195 -0.93037057822878932 0.25486661433158864 -0
		 0.91778928814849914 0.32317414573263831 0.23069740806920488 0 -0.29700038130360962 0.1731157378640252 0.93905362722759544 -0
		 -70.569010513731598 -84.524426128280354 -25.509209034727803 1;
	setAttr ".pm[48]" -type "matrix" -0.092201469831037788 -0.96257046384155609 0.25486661433158864 -0
		 0.97249693640582635 -0.032068903807761735 0.23069740806920488 -0 -0.21388921815340942 0.26912764173978615 0.93905362722759544 -0
		 -92.884403844990771 -54.523672331339355 -25.50924166393435 1;
	setAttr ".pm[49]" -type "matrix" -0.17436652109961107 -0.9511252865790093 0.25486664267733117 -0
		 0.96616935149040428 -0.11530606473741112 0.23069741150559331 -0 -0.19003447203133403 0.28647024394300918 0.9390536186901165 -0
		 -95.183449448266927 -46.536498747224563 -25.50920927407406 1;
	setAttr ".pm[50]" -type "matrix" 0.59060503119176289 -0.73083333885388757 0.34215249224673927 -0
		 0.65963271076872321 0.68147046384253351 0.31699005314701545 0 -0.46483371652116828 0.038479055730619105 0.88456146098233213 -0
		 -29.860193634392186 -107.22872913461252 -30.39536124389673 1;
	setAttr ".pm[51]" -type "matrix" 0.15623819409077636 -0.882834735042898 0.44293617746689945 -0
		 0.90993079452602954 0.30308700144821332 0.28313286408744465 0 -0.38420772490995198 0.35880510051400616 0.85067227765141884 -0
		 -73.837860731263675 -84.413535990483211 -20.992655495034636 1;
	setAttr ".pm[52]" -type "matrix" -0.13914028536523573 -0.88569042203215176 0.44293617746689928 -0
		 0.95903783110518004 -0.0090675124875545798 0.28313286408744448 -0 -0.24675173656440971 0.46418773846127742 0.85067227765141828 -0
		 -92.5554300012748 -57.45383159268782 -20.992631883013306 1;
	setAttr ".pm[53]" -type "matrix" -0.27847973581370616 -0.85220688769344011 0.44293617746689934 -0
		 0.9453417871894082 -0.16175502053159121 0.28313286408744454 -0 -0.16964062642734801 0.49757284280865294 0.85067227765141851 -0
		 -98.291149148823592 -42.333968024759507 -20.992620661524899 1;
	setAttr ".pm[54]" -type "matrix" -0.23677732944738361 0.35804510679136936 0.90318336884739125 -0
		 0.46744570505413796 0.8569327678751999 -0.21716524622551273 0 -0.85172237794143002 0.37076937959398021 -0.37026889967872051 0
		 -43.319422238623893 -78.534515870392084 70.958506589554858 1;
	setAttr ".pm[55]" -type "matrix" -0.045744984989112718 0.47737462528905483 0.87750832672885848 -0
		 0.75995290887936295 0.58677024940003586 -0.27959300904138068 0 -0.64836638764986876 0.65407502746179957 -0.38962403136447582 0
		 -64.345839327249948 -52.176173230388699 76.528256968974361 1;
	setAttr ".pm[56]" -type "matrix" 0.037845217624813077 0.47806576537590528 0.87750832672885837 -0
		 0.8502991008800147 0.44589145353754467 -0.27959300904138062 0 -0.52493730915754944 0.75672579950582142 -0.38962403136447565 -0
		 -69.389506510419253 -40.745817579936116 76.528211143392554 1;
	setAttr ".pm[57]" -type "matrix" 0.3828247169354852 -0.60140250134155371 0.701256206734306 -0
		 0.58595958989830965 0.74492304281562771 0.31896868073293877 0 -0.71421046975626867 0.28879870439880556 0.63757251605452803 -0
		 -27.990338472714193 -111.53948953296096 -11.729855138796443 1;
	setAttr ".pm[58]" -type "matrix" 0.11282515359989771 -0.70392486618372185 0.70125620673430589 -0
		 0.83339914156584216 0.45133673853211298 0.31896868073293871 0 -0.54103267512459507 0.54843863031283846 0.63757251605452792 -0
		 -64.530772805029557 -93.574276600955798 -11.488903496402385 1;
	setAttr ".pm[59]" -type "matrix" -0.071878640927211676 -0.70927652822793241 0.701256206734306 -0
		 0.92140168606377171 0.22198629153694938 0.31896868073293877 -0 -0.38190626323391941 0.66906568651710341 0.63757251605452803 -0
		 -82.469548696630184 -74.894751438847649 -11.48893560306419 1;
	setAttr ".pm[60]" -type "matrix" -0.22388412433854513 -0.67684239774542387 0.70125620673430589 -0
		 0.94761232662282524 0.017025250188002872 0.31896868073293871 -0 -0.22783058903851836 0.73593104939950749 0.63757251605452792 -0
		 -94.207306090605428 -55.804520795970255 -11.488932042382215 1;
	setAttr ".pm[61]" -type "matrix" 0.60649254765026672 -0.029307966948783556 0.79454882336960109 -0
		 0.79463176670612568 0.056235375135533672 -0.60448154473471494 0 -0.026965626011451624 0.99798728732218578 0.057395377489094838 -0
		 -93.385000898837362 -6.0267045524860139 101.69661493443279 1;
	setAttr ".pm[62]" -type "matrix" 0.57603356970190256 -0.03259210070296354 0.81677602899953583 -0
		 0.81709064454343094 0.051578494510997296 -0.57419729841194755 0 -0.023413781755254808 0.99813697150027769 0.056341644883428611 -0
		 -87.916071312962941 -5.4728818388958604 98.116066736292908 1;
	setAttr ".pm[63]" -type "matrix" -0.054523910657437967 -0.1460129330800598 -0.98777900693423215 0
		 -0.99851165534365582 0.0092329884397982145 0.053751521535134128 0 0.0012717348352381784 0.98923959448549592 -0.14629903414814568 -0
		 92.857360147214592 -4.8418851905416949 -14.502292380266628 1;
	setAttr ".pm[64]" -type "matrix" -0.04157786421258719 -0.15021289780688596 -0.98777900693423215 0
		 -0.99551014080239097 -0.077912344928525334 0.053751521535134128 0 -0.085034350512737902 0.98557889173835123 -0.14629903414814568 -0
		 49.749714492727101 -0.50364160660815482 -14.502292380266638 1;
	setAttr ".pm[65]" -type "matrix" 0.0046495256007424747 -0.14803750047914044 -0.98897081876240234 -0
		 -0.99950197930304496 -0.031556184277057558 2.455947517528231e-05 0 -0.031211781124816953 0.98847817663606541 -0.14811049602663426 -0
		 8.26888862648679 -0.85203293990604712 -14.078251050540022 1;
	setAttr ".pm[66]" -type "matrix" 0.14803750047914047 0.0046495256007425059 -0.98897081876240245 -0
		 0.031556184277057787 -0.99950197930304485 2.4559475175282321e-05 0 -0.98847817663606563 -0.031211781124817164 -0.14811049602663426 0
		 16.089627544398237 1.2594520191259586 -13.539305435248426 1;
	setAttr ".pm[67]" -type "matrix" -0.044064310719183056 -0.14803750057573392 -0.98799961282590243 0
		 -0.99828778764580228 -0.031556185440510851 0.049251397926289034 0 -0.038468552846355836 0.98847817658445791 -0.14639352737800065 -0
		 35.680238710006385 -2.1603644829028301 -14.379575794759738 1;
	setAttr ".pm[68]" -type "matrix" -0.044064310719183056 -0.14803750057573392 -0.98799961282590243 0
		 -0.99828778764580228 -0.031556185440510851 0.049251397926289034 0 -0.038468552846355836 0.98847817658445791 -0.14639352737800065 -0
		 21.623113922100643 -1.5061940863598642 -14.480590844561741 1;
	setAttr ".pm[69]" -type "matrix" -0.04672652176680351 -0.14721887520437618 -0.98799961282742177 0
		 -0.99869449405102084 -0.013550178981221499 0.049251397967495926 0 -0.020638306998206981 0.98901111997445967 -0.14639352735388469 -0
		 78.564887298044155 -3.0517164512990425 -14.148382836895289 1;
	setAttr ".pm[70]" -type "matrix" -0.04672652176680351 -0.14721887520437618 -0.98799961282742177 0
		 -0.99869449405102084 -0.013550178981221499 0.049251397967495926 0 -0.020638306998206981 0.98901111997445967 -0.14639352735388469 -0
		 64.121707099473397 -3.3813227074594181 -14.213471789854614 1;
	setAttr ".pm[71]" -type "matrix" -0.05452391065743796 -0.14601293308005972 -0.98777900693423226 -0
		 0.99851165534365627 -0.0092329884397976958 -0.053751521535134204 0 -0.0012717348352376708 -0.98923959448549614 0.14629903414814557 0
		 -92.856783467811482 4.8325715231484505 14.50375024985332 1;
	setAttr ".pm[72]" -type "matrix" -0.04157786421258728 -0.15021289780688588 -0.98777900693423237 0
		 0.99551014080239142 0.077912344928525293 -0.053751521535134204 0 0.085034350512737819 -0.98557889173835178 0.14629903414814563 -0
		 -49.748281886075681 0.49441775222512119 14.503750249853315 1;
	setAttr ".pm[73]" -type "matrix" 0.0046495256007424313 -0.14803750047914024 -0.988970818762402 -0
		 0.99950197930304474 0.031556184277057427 -2.4559475175284022e-05 -0 0.031211781124816783 -0.98847817663606496 0.14811049602663415 -0
		 -8.2680003557588648 0.84275393938400234 14.079758090376085 1;
	setAttr ".pm[74]" -type "matrix" 0.1480375004791403 0.0046495256007424626 -0.98897081876240223 -0
		 -0.031556184277057656 0.99950197930304452 -2.4559475175284902e-05 0 0.98847817663606541 0.031211781124816994 0.14811049602663418 -0
		 -16.080342821830293 -1.2585637483980359 13.540870649217794 1;
	setAttr ".pm[75]" -type "matrix" -0.044064310719183056 -0.14803750057573375 -0.98799961282590198 0
		 0.99828778764580206 0.031556185440510726 -0.049251397926289027 0 0.038468552846355669 -0.98847817658445747 0.14639352737800052 -0
		 -35.679084432099756 2.1510874842858909 14.343308792762238 1;
	setAttr ".pm[76]" -type "matrix" -0.044064310719183056 -0.14803750057573375 -0.98799961282590198 0
		 0.99828778764580206 0.031556185440510726 -0.049251397926289027 0 0.038468552846355669 -0.98847817658445747 0.14639352737800052 -0
		 -21.622141265357996 1.4969094931223024 14.482042566930806 1;
	setAttr ".pm[77]" -type "matrix" -0.046726521766803482 -0.14721887520437607 -0.98799961282742177 0
		 0.99869449405102084 0.013550178981221368 -0.049251397967495905 0 0.020638306998206825 -0.98901111997445967 0.14639352735388458 -0
		 -78.56408960327667 3.0424187130609948 14.149844316139369 1;
	setAttr ".pm[78]" -type "matrix" -0.046726521766803482 -0.14721887520437607 -0.98799961282742177 0
		 0.99869449405102084 0.013550178981221368 -0.049251397967495905 0 0.020638306998206825 -0.98901111997445967 0.14639352735388458 -0
		 -64.120894238196641 3.3720275856538184 14.214941412393523 1;
	setAttr ".gm" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1;
	setAttr -s 79 ".ma";
	setAttr -s 79 ".dpf[0:78]"  4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 
		4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 
		4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4;
	setAttr -s 79 ".lw";
	setAttr -s 79 ".lw";
	setAttr ".mi" 5;
	setAttr ".ucm" yes;
	setAttr -s 79 ".ifcl";
	setAttr -s 79 ".ifcl";
createNode dagPose -n "bindPose1";
	rename -uid "EE516853-4A8C-7AA1-7349-C0817541DDFA";
	setAttr -s 93 ".wm";
	setAttr -s 93 ".xm";
	setAttr ".xm[0]" -type "matrix" "xform" 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 1 -0.70710678118654757 0 0 0.70710678118654757 1 1 1 no;
	setAttr ".xm[1]" -type "matrix" "xform" 1 1 1 -1.5707963267948966 -1.5073866484408736
		 1.5707963267948966 0 -3.4314998759166215e-17 -2.2808661460876465 95.896781921386719 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[2]" -type "matrix" "xform" 0.99999999999999978 0.99999999999999989 1 -8.4954340412815775e-19
		 3.7879761270054613e-18 -0.25232786692436704 0 3.6770534515381001 7.1054273576010019e-15
		 -4.6633694517662434e-16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[3]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 -1.526598595380997e-19
		 3.8327957393595285e-18 0.060466399756961373 0 6.7950572967529155 1.7763568394002505e-14
		 1.8559423937125809e-16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1.0000000000000002 1 no;
	setAttr ".xm[4]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 1.3459375357916401e-18
		 3.7858793145414413e-18 0.19104512581130384 0 7.2382278442382812 -1.9539925233402755e-14
		 1.2292061026364971e-16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999978 1 no;
	setAttr ".xm[5]" -type "matrix" "xform" 1 0.99999999999999989 1 7.8457562572308448e-06
		 -4.1750609512244074e-14 0.10239818677280667 0 8.5238933563232422 -7.1054273576010019e-15
		 2.5229931328786502e-16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999978 1 no;
	setAttr ".xm[6]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 -7.8452173436827024e-06
		 9.3303177584585829e-08 0.011892487809488461 0 19.439800262451158 -1.7817309228007616e-07
		 8.1130192624775943e-13 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1 no;
	setAttr ".xm[7]" -type "matrix" "xform" 1 1 1 -9.2915892070507301e-18 7.0177144030457207e-17
		 -0.41762943546079279 0 11.887765884399442 1.0658141036401503e-14 1.5994409772213136e-15 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978 0.99999999999999978
		 1 no;
	setAttr ".xm[8]" -type "matrix" "xform" 1 0.99999999999999989 1 -1.7098080609365499e-06
		 3.1265086895115411e-16 0.033397375038360995 0 5.1102595329284384 -6.3948846218409017e-14
		 -4.1190754660973504e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[9]" -type "matrix" "xform" 0.99999999999999989 1.0000000000000002 1 1.6732006206635733e-06
		 -3.5198750386794149e-07 0.20734807648447118 0 4.9129710197448446 -4.9737991503207013e-14
		 2.0180004314720307e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1 no;
	setAttr ".xm[10]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000002 0.99999999999999944 2.8494871086844684
		 1.4107710302056788 2.6725246597991861 0 5.5162687301636311 1.3147660493850672
		 -1.4279042482376099 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999978 1 no;
	setAttr ".xm[11]" -type "matrix" "xform" 1 0.99999999999999978 0.99999999999999967 -0.075700955616242127
		 0.80336814696867653 -0.076070501056283102 0 17.809522628784187 1.6431300764452317e-14
		 5.6843418860808015e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 0.99999999999999978 1.0000000000000007 no;
	setAttr ".xm[12]" -type "matrix" "xform" 1.0000000000000002 1 1 -2.0122792321330962e-16
		 6.2450045135165068e-17 -0.68030878144743478 0 27.771139144897504 1.3322676295501878e-14
		 -1.1368683772161603e-13 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1.0000000000000004 no;
	setAttr ".xm[13]" -type "matrix" "xform" 1.0000000000000004 1 1 0.022439294079822175
		 -0.030151140935290543 0.034659238401632195 0 9.0836915969848633 -7.1054273576010019e-14
		 9.9475983006414026e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1 1 no;
	setAttr ".xm[14]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000002 1.0000000000000002 0.022439294486885784
		 -0.030151008698346637 0.034659239879545549 0 18.167383193969734 -2.8421709430404007e-14
		 7.1054273576010019e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1 1 no;
	setAttr ".xm[15]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000011 0.99999999999999956 -1.1828228767081526
		 0.025716916543067354 0.032269676501439172 0 27.251073837280284 -2.1316282072803006e-14
		 9.9475983006414026e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1 1 no;
	setAttr ".xm[16]" -type "matrix" "xform" 0.99999999999999978 0.99999999999999967
		 0.99999999999999978 -0.074569197575235543 -0.0022820379734449945 -0.040463566458286797 0 3.3758335113525533
		 -0.75357073545451669 -0.18286436796188354 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 0.99999999999999978 0.99999999999999889 1.0000000000000004 no;
	setAttr ".xm[17]" -type "matrix" "xform" 1.0000000000000009 1 1.0000000000000004 1.1102230246251568e-16
		 -5.551115123125779e-17 0.5510472548888049 0 6.0982089042663432 5.6843418860808015e-14
		 1.4210854715202004e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1.0000000000000004 1.0000000000000002 no;
	setAttr ".xm[18]" -type "matrix" "xform" 1.0000000000000002 1 1 1.1102230246251565e-16
		 2.4980018054066027e-16 0.36249110587625905 0 5.1690001487731934 -1.4210854715202004e-14
		 4.2632564145606011e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999911
		 1 0.99999999999999956 no;
	setAttr ".xm[19]" -type "matrix" "xform" 1 0.99999999999999989 0.99999999999999967 4.4408920985006271e-16
		 9.7144514654701197e-17 0.17453292469247375 0 2.4739999771118164 4.2632564145606011e-14
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978 1 1 no;
	setAttr ".xm[20]" -type "matrix" "xform" 1.0000000000000002 1 0.99999999999999944 -0.48466133745210704
		 -0.3408227139232512 0.20683246463072913 0 3.3143784999847554 -0.30591726303099165
		 2.3911108970642037 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999889 1.0000000000000004 no;
	setAttr ".xm[21]" -type "matrix" "xform" 1.0000000000000002 1 1.0000000000000002 0.18311366302368809
		 0.010559986230106639 0.25889657159602564 0 4.9575676918029927 -0.14312039315700531
		 -0.19884027540683746 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1 1.0000000000000007 no;
	setAttr ".xm[22]" -type "matrix" "xform" 1.0000000000000004 1 1 -5.5511151231257827e-17
		 -0 0.37152822127820773 0 3.8159999847411825 1.8474111129762605e-13 6.3948846218409017e-14 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978 1 0.99999999999999978 no;
	setAttr ".xm[23]" -type "matrix" "xform" 1 1 1 0 -5.5511151231257827e-17 0.08581784014125636 0 2.0399999618530416
		 7.1054273576010019e-15 1.7763568394002505e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 0.99999999999999956 1 1 no;
	setAttr ".xm[24]" -type "matrix" "xform" 0.99999999999999989 0.99999999999999989
		 0.99999999999999967 -0.23212590879105988 -0.20611149294555786 -0.027830380771128975 0 3.3743038177490234
		 -0.54251688718794355 1.0917565822601283 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999889 1.0000000000000004 no;
	setAttr ".xm[25]" -type "matrix" "xform" 1.0000000000000002 1 1.0000000000000004 0.1116285440033984
		 -0.0020409533590841928 0.51337956704180743 0 5.6455168724060023 -0.041624534875168706
		 -0.020689174532893873 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1.0000000000000002 1.0000000000000004 no;
	setAttr ".xm[26]" -type "matrix" "xform" 1.0000000000000002 1 1.0000000000000002 -5.5511151231257839e-17
		 1.3877787807814452e-16 0.33098423135410443 0 4.9770002365112447 -7.1054273576010019e-14
		 -9.5923269327613525e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1 0.99999999999999956 no;
	setAttr ".xm[27]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 0
		 3.8857805861880474e-16 0.1600117814250466 0 2.265000104904189 3.5527136788005009e-14
		 1.5987211554602254e-13 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1 0.99999999999999978 no;
	setAttr ".xm[28]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000004 0.99999999999999867 1.2839421076547719
		 0.69645929885484559 0.35794391277517801 0 1.992446541786201 1.3566048145294474
		 -2.5815360546112114 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999889 1.0000000000000004 no;
	setAttr ".xm[29]" -type "matrix" "xform" 1 1.0000000000000004 1.0000000000000002 0.061621083266618436
		 -0.033724831256182378 0.40571933881715627 0 4.3779997825622416 9.9475983006414026e-14
		 -7.1054273576010019e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 0.99999999999999956 1.0000000000000013 no;
	setAttr ".xm[30]" -type "matrix" "xform" 1 0.99999999999999978 0.99999999999999989 -5.5511151231257839e-17
		 -5.5511151231257821e-17 0.17453292469247381 0 3.0859999656677246 4.2632564145606011e-14
		 7.1054273576010019e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 0.99999999999999956
		 0.99999999999999978 no;
	setAttr ".xm[31]" -type "matrix" "xform" 1 0.99999999999999956 0.99999999999999989 0.057382000604555151
		 0.12785412347368244 -0.010579529318345349 0 3.4445061683654821 -0.3846808075904562
		 -2.3793244361877459 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999889 1.0000000000000004 no;
	setAttr ".xm[32]" -type "matrix" "xform" 1.0000000000000002 1 1 2.2204460492503141e-16
		 2.2204460492503131e-16 0.40793579989913942 0 5.8770980834960902 0.043181736022219752
		 0.24087569117545549 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000004
		 1.0000000000000002 no;
	setAttr ".xm[33]" -type "matrix" "xform" 1.0000000000000002 0.99999999999999967 0.99999999999999989 5.5511151231257876e-17
		 1.6653345369377348e-16 0.25992435299201333 0 4.0799999237060547 0 -9.0594198809412774e-14 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978 1 1 no;
	setAttr ".xm[34]" -type "matrix" "xform" 1.0000000000000002 0.99999999999999933 1 -5.5511151231257864e-17
		 3.053113317719181e-16 0.21845240790709738 0 2.5950000286102437 7.1054273576010019e-14
		 -2.1316282072803006e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1.0000000000000004 1.0000000000000002 no;
	setAttr ".xm[35]" -type "matrix" "xform" 1.0000000000000002 0.99999999999999978 0.99999999999999956 -0.20276557329418932
		 -0.27590811869800352 0.14865119937913096 0 1.1633778810501241 1.3170588016510436
		 0.51951599121093395 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999889 1.0000000000000004 no;
	setAttr ".xm[36]" -type "matrix" "xform" 1.0000000000000004 0.99999999999999978 1.0000000000000002 4.6824455033833496e-12
		 -0.037582720016429066 -0.0057004004254963374 0 9.2570457458496378 1.1546319456101628e-14
		 -9.9475983006414026e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1.0000000000000004 no;
	setAttr ".xm[37]" -type "matrix" "xform" 1.0000000000000004 0.99999999999999989 1.0000000000000002 -4.8572257327350605e-17
		 7.762887554996208e-17 6.9388939039072253e-18 0 18.514091491699276 8.8817841970012523e-15
		 -9.9475983006414026e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1.0000000000000004 no;
	setAttr ".xm[38]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000004 0.99999999999999967 2.8494871086844702
		 1.4107710302056791 -0.46906799379060754 0 5.5162200927734375 1.314811229705807
		 1.4278726577758791 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999978 1 no;
	setAttr ".xm[39]" -type "matrix" "xform" 1 0.99999999999999978 0.99999999999999944 -0.075700955616242183
		 0.80336814696867653 -0.076070501056282894 0 -17.809625625610355 2.8716144648832653e-06
		 0.00043809693306684494 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 0.99999999999999956 1.0000000000000004 no;
	setAttr ".xm[40]" -type "matrix" "xform" 1 1 1.0000000000000002 -2.0122792321330962e-16
		 2.7061686225238191e-16 -0.6803087814474349 0 -27.770694732666016 -3.4638958368304884e-14
		 5.6843418860808015e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1.0000000000000007 no;
	setAttr ".xm[41]" -type "matrix" "xform" 1 1 1.0000000000000002 0.022439294079822283
		 -0.030151140935290387 0.034659238401632479 0 -9.0836620330810547 -1.4210854715202004e-14
		 -1.4210854715202004e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 0.99999999999999978 no;
	setAttr ".xm[42]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1.0000000000000002 0.022439294486885905
		 -0.030151008698346519 0.034659239879545889 0 -18.167304992675781 -7.1054273576010019e-15
		 -1.4210854715202004e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 0.99999999999999978 no;
	setAttr ".xm[43]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000007 0.99999999999999956 -1.182822876708153
		 0.025716916543067622 0.032269676501439297 0 -27.251010894775412 -7.1054273576010019e-15
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 0.99999999999999978 no;
	setAttr ".xm[44]" -type "matrix" "xform" 0.99999999999999967 0.99999999999999933
		 0.99999999999999989 -0.074569197575235072 -0.0022820379734449399 -0.040463566458286901 0 -3.3758001327514471
		 0.75400394201277265 0.18280552327632194 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999933 1.0000000000000004 no;
	setAttr ".xm[45]" -type "matrix" "xform" 1.0000000000000004 1 1.0000000000000004 1.1102230246251568e-16
		 5.5511151231257815e-17 0.55104725488880479 0 -6.0983657836914205 -0.0001238507247620646
		 1.430381864508945e-06 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000004
		 1.0000000000000007 1.0000000000000002 no;
	setAttr ".xm[46]" -type "matrix" "xform" 1.0000000000000007 1.0000000000000002 1.0000000000000002 5.5511151231257815e-17
		 2.4980018054066007e-16 0.36249110587625921 0 -5.1689915657043315 -7.7438591688405722e-05
		 -3.7045669152746541e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 1 0.99999999999999956 no;
	setAttr ".xm[47]" -type "matrix" "xform" 0.99999999999999989 0.99999999999999989
		 1.0000000000000002 5.5511151231257839e-17 1.8041124150158796e-16 0.17453292469247383 0 -2.4740469455719136
		 4.577730578603223e-05 3.4385015172944122e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 0.99999999999999933 0.99999999999999978 0.99999999999999978 no;
	setAttr ".xm[48]" -type "matrix" "xform" 0.99999999999999989 0.99999999999999978
		 0.99999999999999944 -0.48466133745210677 -0.34082271392325142 0.20683246463072907 0 -3.3146772384643484
		 0.30593535304068098 -2.3912868499755913 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999933 1.0000000000000004 no;
	setAttr ".xm[49]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000002 1.0000000000000004 0.18311366302368837
		 0.010559986230106516 0.25889657159602564 0 -4.9573006629943919 0.14326146245002747
		 0.19892024993895774 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1.0000000000000002 1.0000000000000007 no;
	setAttr ".xm[50]" -type "matrix" "xform" 1 0.99999999999999989 1.0000000000000002 1.110223024625157e-16
		 2.4980018054066027e-16 0.37152822127820773 0 -3.8160362243652344 3.0366025399075625e-05
		 3.2629206547341028e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 0.99999999999999978 0.99999999999999956 no;
	setAttr ".xm[51]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000002 1.0000000000000007 2.9802322609739917e-08
		 1.6653345348697833e-16 0.085817840141256277 0 -2.0399997234344625 -1.7523876529423887e-05
		 -3.1002964529847077e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 0.99999999999999978 no;
	setAttr ".xm[52]" -type "matrix" "xform" 0.99999999999999978 0.99999999999999978
		 0.99999999999999978 -0.23212590879105943 -0.20611149294555794 -0.027830380771128815 0 -3.3742079734802175
		 0.54299175739286909 -1.0917816162109411 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999933 1.0000000000000004 no;
	setAttr ".xm[53]" -type "matrix" "xform" 1 0.99999999999999989 1.0000000000000002 0.11162854400339839
		 -0.0020409533590840857 0.51337956704180732 0 -5.6457118988037216 0.041443493217229843
		 0.02067497372626903 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1.0000000000000002 1.0000000000000002 no;
	setAttr ".xm[54]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000002 1.0000000000000002 1.6653345369377346e-16
		 -5.5511151231257796e-17 0.3309842313541051 0 -4.9770674705505371 -2.0846833649557084e-05
		 -2.3612021323060617e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 0.99999999999999978 no;
	setAttr ".xm[55]" -type "matrix" "xform" 1 0.99999999999999956 1 1.110223024625157e-16
		 -1.1102230246251565e-16 0.1600117814250463 0 -2.2649745941161967 5.0017570174532011e-05
		 -1.1221488421142567e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 0.99999999999999978 0.99999999999999978 no;
	setAttr ".xm[56]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 0.99999999999999867 1.2839421076547719
		 0.69645929885484559 0.35794391277517801 0 -1.9928325414657593 -1.3566571474075317
		 2.5813255310058487 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999933 1.0000000000000004 no;
	setAttr ".xm[57]" -type "matrix" "xform" 0.99999999999999989 1 1 0.061621083266618769
		 -0.033724831256182371 0.40571933881715622 0 -4.3778247833251811 0.00042712956201285124
		 -0.00013574546028394252 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999978 1.0000000000000013 no;
	setAttr ".xm[58]" -type "matrix" "xform" 0.99999999999999989 1.0000000000000002 1.0000000000000002 2.2204460492503128e-16
		 2.775557561562892e-17 0.174532924692474 0 -3.0859522819519114 -1.4851160820228415e-05
		 4.5825581779013191e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1 1 no;
	setAttr ".xm[59]" -type "matrix" "xform" 0.99999999999999978 0.99999999999999967
		 0.99999999999999989 0.057382000604555554 0.12785412347368241 -0.010579529318345288 0 -3.4445140361785747
		 0.38516682386398315 2.3793087005615163 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999933 1.0000000000000004 no;
	setAttr ".xm[60]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 1.6653345369377356e-16
		 -6.1629758220391561e-33 0.40793579989913936 0 -5.8772053718566966 -0.043412361294045354
		 -0.24095164239406408 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1.0000000000000004 1.0000000000000002 no;
	setAttr ".xm[61]" -type "matrix" "xform" 0.99999999999999956 0.99999999999999956
		 1 1.6653345369377363e-16 -2.7755575615628938e-17 0.25992435299201333 0 -4.079932689666748
		 5.0402059201815064e-06 3.2106661814523818e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 0.99999999999999978 0.99999999999999978 1 no;
	setAttr ".xm[62]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 5.5511151231257827e-17
		 -7.7037197775489451e-34 0.21845240790709736 0 -2.5950763225555562 3.9602185992748673e-05
		 -3.5606819821509816e-06 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000004
		 1.0000000000000004 1 no;
	setAttr ".xm[63]" -type "matrix" "xform" 1 0.99999999999999978 0.99999999999999967 -0.20276557828828717
		 -0.2759081145953387 0.14865123738628735 0 -1.1633833646774221 -1.3170545101165771
		 -0.51951736211777799 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999933 1.0000000000000004 no;
	setAttr ".xm[64]" -type "matrix" "xform" 1.0000000000000002 0.99999999999999978 1.0000000000000002 4.6825010808855376e-12
		 -0.037582720016428761 -0.0057004004254963235 0 -9.2568979263305522 1.0202637897194222e-05
		 -0.00010078256310919187 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1.0000000000000007 no;
	setAttr ".xm[65]" -type "matrix" "xform" 1.0000000000000002 1 1.0000000000000002 3.4694469519536142e-17
		 1.8496489062602701e-16 -2.0816681711721682e-17 0 -18.513795852661133 2.0405275791723909e-05
		 -0.00020156512620417288 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1.0000000000000007 no;
	setAttr ".xm[66]" -type "matrix" "xform" 1 0.99999999999999989 1 0.14675668491959673
		 -0.05455096215892502 3.0794566049833967 0 -2.3657262325286723 -0.11948779225349782
		 9.9690914154052734 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[67]" -type "matrix" "xform" 0.99999999999999967 0.99999999999999989
		 1 -1.1102230246251568e-16 -8.1532003370909958e-17 -0.087351016050521424 0 43.341262817382777
		 -2.5757174171303632e-14 1.0658141036401503e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 1 1.0000000000000002 1 no;
	setAttr ".xm[68]" -type "matrix" "xform" 0.99999999999999989 1.0000000000000002 1.0000000000000002 -8.1377868058169335e-05
		 0.05377711914424417 0.04649739873768536 0 42.217948913574233 1.1102230246251565e-16
		 1.0658141036401503e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000004
		 1.0000000000000002 1 no;
	setAttr ".xm[69]" -type "matrix" "xform" 0.99999999999999967 1 0.99999999999999978 1.2177758801357188e-15
		 -1.1379786002407858e-15 -1.5707963267948968 0 7.0094366073608354 15.237594604492184
		 -0.53894561529159546 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 0.99999999999999978 0.99999999999999978 no;
	setAttr ".xm[70]" -type "matrix" "xform" 0.99999999999999989 0.99999999999999967
		 1 -8.1261009348669198e-05 0.0045057895521491333 0.046501405584295427 0 14.072649955749519
		 6.8833827526759706e-15 0.037728950381282544 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 1.0000000000000004 1.0000000000000002 1 no;
	setAttr ".xm[71]" -type "matrix" "xform" 0.99999999999999989 0.99999999999999967
		 1 -8.1261009348669198e-05 0.0045057895521491333 0.046501405584295427 0 28.145299911499034
		 8.4376949871511897e-15 0.075457900762563312 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 1.0000000000000004 1.0000000000000002 1 no;
	setAttr ".xm[72]" -type "matrix" "xform" 0.99999999999999956 1 0.99999999999999989 -3.604153589139624e-12
		 0.0045065222090264426 -0.022816700021501331 0 14.447087287902804 -3.5527136788005009e-15
		 -3.5527136788005009e-15 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1 no;
	setAttr ".xm[73]" -type "matrix" "xform" 0.99999999999999956 1 0.99999999999999989 -3.604153589139624e-12
		 0.0045065222090264426 -0.022816700021501331 0 28.894174575805629 -1.2434497875801753e-14
		 -3.3750779948604759e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1 no;
	setAttr ".xm[74]" -type "matrix" "xform" 1 1 1 0.14675668491959665 -0.054550962158925013
		 -0.062136048606397057 0 -2.3657112121582031 -0.11004376411438344 -9.969202995300293 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[75]" -type "matrix" "xform" 0.99999999999999967 0.99999999999999967
		 0.99999999999999989 -5.5511151231257864e-17 -0 -0.087351016050520799 0 -43.341308593749993
		 6.2172489379008766e-15 5.3290705182007514e-15 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 1 1 1 no;
	setAttr ".xm[76]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000011 1.0000000000000004 -8.1377868058141756e-05
		 0.053777119144244226 0.046497398737685401 0 -42.217914581298842 -3.5527136788005009e-15
		 5.3290705182007514e-15 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000004
		 1.0000000000000004 1.0000000000000002 no;
	setAttr ".xm[77]" -type "matrix" "xform" 0.99999999999999956 1.0000000000000002 0.99999999999999978 1.5785983631388942e-16
		 -1.110223024625157e-16 -1.5707963267948968 0 -7.0094366073608327 -15.237588882446284
		 0.53888744115829468 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 0.99999999999999889 0.99999999999999956 no;
	setAttr ".xm[78]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000004 1.0000000000000004 -8.1261009348641429e-05
		 0.0045057895521491897 0.046501405584295455 0 -14.072638511657715 1.7763568394002505e-15
		 1.9539925233402755e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000004
		 1.0000000000000004 1.0000000000000002 no;
	setAttr ".xm[79]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000004 1.0000000000000004 -8.1261009348641429e-05
		 0.0045057895521491897 0.046501405584295455 0 -28.145277023315437 5.0670109880135428e-06
		 -0.075448110699655402 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000004
		 1.0000000000000004 1.0000000000000002 no;
	setAttr ".xm[80]" -type "matrix" "xform" 0.99999999999999978 1 0.99999999999999978 -3.6040425792624552e-12
		 0.0045065222090265337 -0.022816700021500678 0 -14.447102546691895 8.8817841970012523e-16
		 3.5527136788005009e-15 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[81]" -type "matrix" "xform" 0.99999999999999978 1 0.99999999999999978 -3.6040425792624552e-12
		 0.0045065222090265337 -0.022816700021500678 0 -28.894205093383796 -2.2688980125806779e-06
		 -8.0748641266836785e-06 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[82]" -type "matrix" "xform" 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[83]" -type "matrix" "xform" 0.99999999999999978 0.99999999999999978
		 1 1.1950811745653398 -0.68783621143055862 0.93665733272538276 0 -47.768318176269531
		 -15.69880485534668 104.4664306640625 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1
		 1 1 no;
	setAttr ".xm[84]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 5.8286708792820709e-16
		 -3.8857805861880469e-16 0 0 -7.1054273576010019e-15 0 7.1054273576010019e-15 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002 1.0000000000000002
		 1 no;
	setAttr ".xm[85]" -type "matrix" "xform" 1 1 1 -1.8803756031765697 -0.59405406535441252
		 -2.347589926485619 0 43.73357009887696 -61.669849395751982 58.408111572265597 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002 1.0000000000000002
		 1 no;
	setAttr ".xm[86]" -type "matrix" "xform" 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[87]" -type "matrix" "xform" 1 0.99999999999999978 0.99999999999999978 1.5715746675411471
		 -1.5392348934121391 -1.4229168665858918 0 14.087671279907227 0.99425750970840454
		 8.2376375198364258 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[88]" -type "matrix" "xform" 1 0.99999999999999956 0.99999999999999978 -1.5700179860486321
		 1.5392348934121391 1.4229168665858849 0 -14.087558746337891 0.98483455181121826
		 8.2382316589355469 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[89]" -type "matrix" "xform" 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[90]" -type "matrix" "xform" 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[91]" -type "matrix" "xform" 1 1 1 0 0 0 0 2.8421709430404007e-14
		 0 168 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[92]" -type "matrix" "xform" 1 1 1 0 0 0 0 0 0 -3 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr -s 93 ".m";
	setAttr -s 93 ".p";
	setAttr ".bp" yes;
select -ne :time1;
	setAttr ".o" 0;
select -ne :hardwareRenderingGlobals;
	setAttr ".otfna" -type "stringArray" 22 "NURBS Curves" "NURBS Surfaces" "Polygons" "Subdiv Surface" "Particles" "Particle Instance" "Fluids" "Strokes" "Image Planes" "UI" "Lights" "Cameras" "Locators" "Joints" "IK Handles" "Deformers" "Motion Trails" "Components" "Hair Systems" "Follicles" "Misc. UI" "Ornaments"  ;
	setAttr ".otfva" -type "Int32Array" 22 0 1 1 1 1 1
		 1 1 1 0 0 0 0 0 0 0 0 0
		 0 0 0 0 ;
	setAttr ".fprt" yes;
	setAttr ".rtfm" 1;
select -ne :renderPartition;
	setAttr -s 2 ".st";
select -ne :renderGlobalsList1;
select -ne :defaultShaderList1;
	setAttr -s 6 ".s";
select -ne :postProcessList1;
	setAttr -s 2 ".p";
select -ne :defaultRenderingList1;
select -ne :standardSurface1;
	setAttr ".bc" -type "float3" 0.40000001 0.40000001 0.40000001 ;
	setAttr ".sr" 0.5;
select -ne :openPBR_shader1;
	setAttr ".bc" -type "float3" 0.40000001 0.40000001 0.40000001 ;
	setAttr ".sr" 0.5;
select -ne :initialShadingGroup;
	setAttr ".ro" yes;
select -ne :initialParticleSE;
	setAttr ".ro" yes;
select -ne :defaultRenderGlobals;
	addAttr -ci true -h true -sn "dss" -ln "defaultSurfaceShader" -dt "string";
	setAttr ".dss" -type "string" "openPBR_shader1";
select -ne :defaultResolution;
	setAttr ".pa" 1;
select -ne :defaultColorMgtGlobals;
	setAttr ".cfe" yes;
	setAttr ".cfp" -type "string" "<MAYA_RESOURCES>/OCIO-configs/Maya2022-default/config.ocio";
	setAttr ".vtn" -type "string" "ACES 1.0 SDR-video (sRGB)";
	setAttr ".vn" -type "string" "ACES 1.0 SDR-video";
	setAttr ".dn" -type "string" "sRGB";
	setAttr ".wsn" -type "string" "ACEScg";
	setAttr ".otn" -type "string" "ACES 1.0 SDR-video (sRGB)";
	setAttr ".potn" -type "string" "ACES 1.0 SDR-video (sRGB)";
select -ne :hardwareRenderGlobals;
	setAttr ".ctrs" 256;
	setAttr ".btrs" 512;
connectAttr "root.s" "pelvis.is";
connectAttr "pelvis.s" "spine_01.is";
connectAttr "spine_01.s" "spine_02.is";
connectAttr "spine_02.s" "spine_03.is";
connectAttr "spine_03.s" "spine_04.is";
connectAttr "spine_04.s" "spine_05.is";
connectAttr "spine_05.s" "neck_01.is";
connectAttr "neck_01.s" "neck_02.is";
connectAttr "neck_02.s" "head.is";
connectAttr "spine_05.s" "clavicle_l.is";
connectAttr "clavicle_l.s" "upperarm_l.is";
connectAttr "upperarm_l.s" "lowerarm_l.is";
connectAttr "lowerarm_l.s" "lowerarm_twist_02_l.is";
connectAttr "lowerarm_l.s" "lowerarm_twist_01_l.is";
connectAttr "lowerarm_l.s" "hand_l.is";
connectAttr "hand_l.s" "middle_metacarpal_l.is";
connectAttr "middle_metacarpal_l.s" "middle_01_l.is";
connectAttr "middle_01_l.s" "middle_02_l.is";
connectAttr "middle_02_l.s" "middle_03_l.is";
connectAttr "hand_l.s" "pinky_metacarpal_l.is";
connectAttr "pinky_metacarpal_l.s" "pinky_01_l.is";
connectAttr "pinky_01_l.s" "pinky_02_l.is";
connectAttr "pinky_02_l.s" "pinky_03_l.is";
connectAttr "hand_l.s" "ring_metacarpal_l.is";
connectAttr "ring_metacarpal_l.s" "ring_01_l.is";
connectAttr "ring_01_l.s" "ring_02_l.is";
connectAttr "ring_02_l.s" "ring_03_l.is";
connectAttr "hand_l.s" "thumb_01_l.is";
connectAttr "thumb_01_l.s" "thumb_02_l.is";
connectAttr "thumb_02_l.s" "thumb_03_l.is";
connectAttr "hand_l.s" "index_metacarpal_l.is";
connectAttr "index_metacarpal_l.s" "index_01_l.is";
connectAttr "index_01_l.s" "index_02_l.is";
connectAttr "index_02_l.s" "index_03_l.is";
connectAttr "hand_l.s" "weapon_l.is";
connectAttr "upperarm_l.s" "upperarm_twist_01_l.is";
connectAttr "upperarm_l.s" "upperarm_twist_02_l.is";
connectAttr "spine_05.s" "clavicle_r.is";
connectAttr "clavicle_r.s" "upperarm_r.is";
connectAttr "upperarm_r.s" "lowerarm_r.is";
connectAttr "lowerarm_r.s" "lowerarm_twist_02_r.is";
connectAttr "lowerarm_r.s" "lowerarm_twist_01_r.is";
connectAttr "lowerarm_r.s" "hand_r.is";
connectAttr "hand_r.s" "middle_metacarpal_r.is";
connectAttr "middle_metacarpal_r.s" "middle_01_r.is";
connectAttr "middle_01_r.s" "middle_02_r.is";
connectAttr "middle_02_r.s" "middle_03_r.is";
connectAttr "hand_r.s" "pinky_metacarpal_r.is";
connectAttr "pinky_metacarpal_r.s" "pinky_01_r.is";
connectAttr "pinky_01_r.s" "pinky_02_r.is";
connectAttr "pinky_02_r.s" "pinky_03_r.is";
connectAttr "hand_r.s" "ring_metacarpal_r.is";
connectAttr "ring_metacarpal_r.s" "ring_01_r.is";
connectAttr "ring_01_r.s" "ring_02_r.is";
connectAttr "ring_02_r.s" "ring_03_r.is";
connectAttr "hand_r.s" "thumb_01_r.is";
connectAttr "thumb_01_r.s" "thumb_02_r.is";
connectAttr "thumb_02_r.s" "thumb_03_r.is";
connectAttr "hand_r.s" "index_metacarpal_r.is";
connectAttr "index_metacarpal_r.s" "index_01_r.is";
connectAttr "index_01_r.s" "index_02_r.is";
connectAttr "index_02_r.s" "index_03_r.is";
connectAttr "hand_r.s" "weapon_r.is";
connectAttr "upperarm_r.s" "upperarm_twist_01_r.is";
connectAttr "upperarm_r.s" "upperarm_twist_02_r.is";
connectAttr "pelvis.s" "thigh_r.is";
connectAttr "thigh_r.s" "calf_r.is";
connectAttr "calf_r.s" "foot_r.is";
connectAttr "foot_r.s" "ball_r.is";
connectAttr "calf_r.s" "calf_twist_02_r.is";
connectAttr "calf_r.s" "calf_twist_01_r.is";
connectAttr "thigh_r.s" "thigh_twist_01_r.is";
connectAttr "thigh_r.s" "thigh_twist_02_r.is";
connectAttr "pelvis.s" "thigh_l.is";
connectAttr "thigh_l.s" "calf_l.is";
connectAttr "calf_l.s" "foot_l.is";
connectAttr "foot_l.s" "ball_l.is";
connectAttr "calf_l.s" "calf_twist_02_l.is";
connectAttr "calf_l.s" "calf_twist_01_l.is";
connectAttr "thigh_l.s" "thigh_twist_01_l.is";
connectAttr "thigh_l.s" "thigh_twist_02_l.is";
connectAttr "root.s" "ik_hand_root.is";
connectAttr "ik_hand_root.s" "ik_hand_gun.is";
connectAttr "ik_hand_gun.s" "ik_hand_r.is";
connectAttr "ik_hand_gun.s" "ik_hand_l.is";
connectAttr "root.s" "ik_foot_root.is";
connectAttr "ik_foot_root.s" "ik_foot_l.is";
connectAttr "ik_foot_root.s" "ik_foot_r.is";
connectAttr "root.s" "interaction.is";
connectAttr "root.s" "center_of_mass.is";
connectAttr "root.s" "camera_root.is";
connectAttr "camera_root.s" "camera_bone.is";
connectAttr "Skirt_skinCluster.og[0]" "SkirtShape.i";
relationship "link" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "link" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
connectAttr "layerManager.dli[0]" "defaultLayer.id";
connectAttr "renderLayerManager.rlmi[0]" "defaultRenderLayer.rlid";
connectAttr "SkirtShapeOrig.w" "Skirt_skinCluster.ip[0].ig";
connectAttr "SkirtShapeOrig.o" "Skirt_skinCluster.orggeom[0]";
connectAttr "pelvis.wm" "Skirt_skinCluster.ma[0]";
connectAttr "spine_01.wm" "Skirt_skinCluster.ma[1]";
connectAttr "spine_02.wm" "Skirt_skinCluster.ma[2]";
connectAttr "spine_03.wm" "Skirt_skinCluster.ma[3]";
connectAttr "spine_04.wm" "Skirt_skinCluster.ma[4]";
connectAttr "spine_05.wm" "Skirt_skinCluster.ma[5]";
connectAttr "neck_01.wm" "Skirt_skinCluster.ma[6]";
connectAttr "neck_02.wm" "Skirt_skinCluster.ma[7]";
connectAttr "head.wm" "Skirt_skinCluster.ma[8]";
connectAttr "clavicle_l.wm" "Skirt_skinCluster.ma[9]";
connectAttr "upperarm_l.wm" "Skirt_skinCluster.ma[10]";
connectAttr "lowerarm_l.wm" "Skirt_skinCluster.ma[11]";
connectAttr "lowerarm_twist_02_l.wm" "Skirt_skinCluster.ma[12]";
connectAttr "lowerarm_twist_01_l.wm" "Skirt_skinCluster.ma[13]";
connectAttr "hand_l.wm" "Skirt_skinCluster.ma[14]";
connectAttr "middle_metacarpal_l.wm" "Skirt_skinCluster.ma[15]";
connectAttr "middle_01_l.wm" "Skirt_skinCluster.ma[16]";
connectAttr "middle_02_l.wm" "Skirt_skinCluster.ma[17]";
connectAttr "middle_03_l.wm" "Skirt_skinCluster.ma[18]";
connectAttr "pinky_metacarpal_l.wm" "Skirt_skinCluster.ma[19]";
connectAttr "pinky_01_l.wm" "Skirt_skinCluster.ma[20]";
connectAttr "pinky_02_l.wm" "Skirt_skinCluster.ma[21]";
connectAttr "pinky_03_l.wm" "Skirt_skinCluster.ma[22]";
connectAttr "ring_metacarpal_l.wm" "Skirt_skinCluster.ma[23]";
connectAttr "ring_01_l.wm" "Skirt_skinCluster.ma[24]";
connectAttr "ring_02_l.wm" "Skirt_skinCluster.ma[25]";
connectAttr "ring_03_l.wm" "Skirt_skinCluster.ma[26]";
connectAttr "thumb_01_l.wm" "Skirt_skinCluster.ma[27]";
connectAttr "thumb_02_l.wm" "Skirt_skinCluster.ma[28]";
connectAttr "thumb_03_l.wm" "Skirt_skinCluster.ma[29]";
connectAttr "index_metacarpal_l.wm" "Skirt_skinCluster.ma[30]";
connectAttr "index_01_l.wm" "Skirt_skinCluster.ma[31]";
connectAttr "index_02_l.wm" "Skirt_skinCluster.ma[32]";
connectAttr "index_03_l.wm" "Skirt_skinCluster.ma[33]";
connectAttr "upperarm_twist_01_l.wm" "Skirt_skinCluster.ma[34]";
connectAttr "upperarm_twist_02_l.wm" "Skirt_skinCluster.ma[35]";
connectAttr "clavicle_r.wm" "Skirt_skinCluster.ma[36]";
connectAttr "upperarm_r.wm" "Skirt_skinCluster.ma[37]";
connectAttr "lowerarm_r.wm" "Skirt_skinCluster.ma[38]";
connectAttr "lowerarm_twist_02_r.wm" "Skirt_skinCluster.ma[39]";
connectAttr "lowerarm_twist_01_r.wm" "Skirt_skinCluster.ma[40]";
connectAttr "hand_r.wm" "Skirt_skinCluster.ma[41]";
connectAttr "middle_metacarpal_r.wm" "Skirt_skinCluster.ma[42]";
connectAttr "middle_01_r.wm" "Skirt_skinCluster.ma[43]";
connectAttr "middle_02_r.wm" "Skirt_skinCluster.ma[44]";
connectAttr "middle_03_r.wm" "Skirt_skinCluster.ma[45]";
connectAttr "pinky_metacarpal_r.wm" "Skirt_skinCluster.ma[46]";
connectAttr "pinky_01_r.wm" "Skirt_skinCluster.ma[47]";
connectAttr "pinky_02_r.wm" "Skirt_skinCluster.ma[48]";
connectAttr "pinky_03_r.wm" "Skirt_skinCluster.ma[49]";
connectAttr "ring_metacarpal_r.wm" "Skirt_skinCluster.ma[50]";
connectAttr "ring_01_r.wm" "Skirt_skinCluster.ma[51]";
connectAttr "ring_02_r.wm" "Skirt_skinCluster.ma[52]";
connectAttr "ring_03_r.wm" "Skirt_skinCluster.ma[53]";
connectAttr "thumb_01_r.wm" "Skirt_skinCluster.ma[54]";
connectAttr "thumb_02_r.wm" "Skirt_skinCluster.ma[55]";
connectAttr "thumb_03_r.wm" "Skirt_skinCluster.ma[56]";
connectAttr "index_metacarpal_r.wm" "Skirt_skinCluster.ma[57]";
connectAttr "index_01_r.wm" "Skirt_skinCluster.ma[58]";
connectAttr "index_02_r.wm" "Skirt_skinCluster.ma[59]";
connectAttr "index_03_r.wm" "Skirt_skinCluster.ma[60]";
connectAttr "upperarm_twist_01_r.wm" "Skirt_skinCluster.ma[61]";
connectAttr "upperarm_twist_02_r.wm" "Skirt_skinCluster.ma[62]";
connectAttr "thigh_r.wm" "Skirt_skinCluster.ma[63]";
connectAttr "calf_r.wm" "Skirt_skinCluster.ma[64]";
connectAttr "foot_r.wm" "Skirt_skinCluster.ma[65]";
connectAttr "ball_r.wm" "Skirt_skinCluster.ma[66]";
connectAttr "calf_twist_02_r.wm" "Skirt_skinCluster.ma[67]";
connectAttr "calf_twist_01_r.wm" "Skirt_skinCluster.ma[68]";
connectAttr "thigh_twist_01_r.wm" "Skirt_skinCluster.ma[69]";
connectAttr "thigh_twist_02_r.wm" "Skirt_skinCluster.ma[70]";
connectAttr "thigh_l.wm" "Skirt_skinCluster.ma[71]";
connectAttr "calf_l.wm" "Skirt_skinCluster.ma[72]";
connectAttr "foot_l.wm" "Skirt_skinCluster.ma[73]";
connectAttr "ball_l.wm" "Skirt_skinCluster.ma[74]";
connectAttr "calf_twist_02_l.wm" "Skirt_skinCluster.ma[75]";
connectAttr "calf_twist_01_l.wm" "Skirt_skinCluster.ma[76]";
connectAttr "thigh_twist_01_l.wm" "Skirt_skinCluster.ma[77]";
connectAttr "thigh_twist_02_l.wm" "Skirt_skinCluster.ma[78]";
connectAttr "pelvis.liw" "Skirt_skinCluster.lw[0]";
connectAttr "spine_01.liw" "Skirt_skinCluster.lw[1]";
connectAttr "spine_02.liw" "Skirt_skinCluster.lw[2]";
connectAttr "spine_03.liw" "Skirt_skinCluster.lw[3]";
connectAttr "spine_04.liw" "Skirt_skinCluster.lw[4]";
connectAttr "spine_05.liw" "Skirt_skinCluster.lw[5]";
connectAttr "neck_01.liw" "Skirt_skinCluster.lw[6]";
connectAttr "neck_02.liw" "Skirt_skinCluster.lw[7]";
connectAttr "head.liw" "Skirt_skinCluster.lw[8]";
connectAttr "clavicle_l.liw" "Skirt_skinCluster.lw[9]";
connectAttr "upperarm_l.liw" "Skirt_skinCluster.lw[10]";
connectAttr "lowerarm_l.liw" "Skirt_skinCluster.lw[11]";
connectAttr "lowerarm_twist_02_l.liw" "Skirt_skinCluster.lw[12]";
connectAttr "lowerarm_twist_01_l.liw" "Skirt_skinCluster.lw[13]";
connectAttr "hand_l.liw" "Skirt_skinCluster.lw[14]";
connectAttr "middle_metacarpal_l.liw" "Skirt_skinCluster.lw[15]";
connectAttr "middle_01_l.liw" "Skirt_skinCluster.lw[16]";
connectAttr "middle_02_l.liw" "Skirt_skinCluster.lw[17]";
connectAttr "middle_03_l.liw" "Skirt_skinCluster.lw[18]";
connectAttr "pinky_metacarpal_l.liw" "Skirt_skinCluster.lw[19]";
connectAttr "pinky_01_l.liw" "Skirt_skinCluster.lw[20]";
connectAttr "pinky_02_l.liw" "Skirt_skinCluster.lw[21]";
connectAttr "pinky_03_l.liw" "Skirt_skinCluster.lw[22]";
connectAttr "ring_metacarpal_l.liw" "Skirt_skinCluster.lw[23]";
connectAttr "ring_01_l.liw" "Skirt_skinCluster.lw[24]";
connectAttr "ring_02_l.liw" "Skirt_skinCluster.lw[25]";
connectAttr "ring_03_l.liw" "Skirt_skinCluster.lw[26]";
connectAttr "thumb_01_l.liw" "Skirt_skinCluster.lw[27]";
connectAttr "thumb_02_l.liw" "Skirt_skinCluster.lw[28]";
connectAttr "thumb_03_l.liw" "Skirt_skinCluster.lw[29]";
connectAttr "index_metacarpal_l.liw" "Skirt_skinCluster.lw[30]";
connectAttr "index_01_l.liw" "Skirt_skinCluster.lw[31]";
connectAttr "index_02_l.liw" "Skirt_skinCluster.lw[32]";
connectAttr "index_03_l.liw" "Skirt_skinCluster.lw[33]";
connectAttr "upperarm_twist_01_l.liw" "Skirt_skinCluster.lw[34]";
connectAttr "upperarm_twist_02_l.liw" "Skirt_skinCluster.lw[35]";
connectAttr "clavicle_r.liw" "Skirt_skinCluster.lw[36]";
connectAttr "upperarm_r.liw" "Skirt_skinCluster.lw[37]";
connectAttr "lowerarm_r.liw" "Skirt_skinCluster.lw[38]";
connectAttr "lowerarm_twist_02_r.liw" "Skirt_skinCluster.lw[39]";
connectAttr "lowerarm_twist_01_r.liw" "Skirt_skinCluster.lw[40]";
connectAttr "hand_r.liw" "Skirt_skinCluster.lw[41]";
connectAttr "middle_metacarpal_r.liw" "Skirt_skinCluster.lw[42]";
connectAttr "middle_01_r.liw" "Skirt_skinCluster.lw[43]";
connectAttr "middle_02_r.liw" "Skirt_skinCluster.lw[44]";
connectAttr "middle_03_r.liw" "Skirt_skinCluster.lw[45]";
connectAttr "pinky_metacarpal_r.liw" "Skirt_skinCluster.lw[46]";
connectAttr "pinky_01_r.liw" "Skirt_skinCluster.lw[47]";
connectAttr "pinky_02_r.liw" "Skirt_skinCluster.lw[48]";
connectAttr "pinky_03_r.liw" "Skirt_skinCluster.lw[49]";
connectAttr "ring_metacarpal_r.liw" "Skirt_skinCluster.lw[50]";
connectAttr "ring_01_r.liw" "Skirt_skinCluster.lw[51]";
connectAttr "ring_02_r.liw" "Skirt_skinCluster.lw[52]";
connectAttr "ring_03_r.liw" "Skirt_skinCluster.lw[53]";
connectAttr "thumb_01_r.liw" "Skirt_skinCluster.lw[54]";
connectAttr "thumb_02_r.liw" "Skirt_skinCluster.lw[55]";
connectAttr "thumb_03_r.liw" "Skirt_skinCluster.lw[56]";
connectAttr "index_metacarpal_r.liw" "Skirt_skinCluster.lw[57]";
connectAttr "index_01_r.liw" "Skirt_skinCluster.lw[58]";
connectAttr "index_02_r.liw" "Skirt_skinCluster.lw[59]";
connectAttr "index_03_r.liw" "Skirt_skinCluster.lw[60]";
connectAttr "upperarm_twist_01_r.liw" "Skirt_skinCluster.lw[61]";
connectAttr "upperarm_twist_02_r.liw" "Skirt_skinCluster.lw[62]";
connectAttr "thigh_r.liw" "Skirt_skinCluster.lw[63]";
connectAttr "calf_r.liw" "Skirt_skinCluster.lw[64]";
connectAttr "foot_r.liw" "Skirt_skinCluster.lw[65]";
connectAttr "ball_r.liw" "Skirt_skinCluster.lw[66]";
connectAttr "calf_twist_02_r.liw" "Skirt_skinCluster.lw[67]";
connectAttr "calf_twist_01_r.liw" "Skirt_skinCluster.lw[68]";
connectAttr "thigh_twist_01_r.liw" "Skirt_skinCluster.lw[69]";
connectAttr "thigh_twist_02_r.liw" "Skirt_skinCluster.lw[70]";
connectAttr "thigh_l.liw" "Skirt_skinCluster.lw[71]";
connectAttr "calf_l.liw" "Skirt_skinCluster.lw[72]";
connectAttr "foot_l.liw" "Skirt_skinCluster.lw[73]";
connectAttr "ball_l.liw" "Skirt_skinCluster.lw[74]";
connectAttr "calf_twist_02_l.liw" "Skirt_skinCluster.lw[75]";
connectAttr "calf_twist_01_l.liw" "Skirt_skinCluster.lw[76]";
connectAttr "thigh_twist_01_l.liw" "Skirt_skinCluster.lw[77]";
connectAttr "thigh_twist_02_l.liw" "Skirt_skinCluster.lw[78]";
connectAttr "pelvis.obcc" "Skirt_skinCluster.ifcl[0]";
connectAttr "spine_01.obcc" "Skirt_skinCluster.ifcl[1]";
connectAttr "spine_02.obcc" "Skirt_skinCluster.ifcl[2]";
connectAttr "spine_03.obcc" "Skirt_skinCluster.ifcl[3]";
connectAttr "spine_04.obcc" "Skirt_skinCluster.ifcl[4]";
connectAttr "spine_05.obcc" "Skirt_skinCluster.ifcl[5]";
connectAttr "neck_01.obcc" "Skirt_skinCluster.ifcl[6]";
connectAttr "neck_02.obcc" "Skirt_skinCluster.ifcl[7]";
connectAttr "head.obcc" "Skirt_skinCluster.ifcl[8]";
connectAttr "clavicle_l.obcc" "Skirt_skinCluster.ifcl[9]";
connectAttr "upperarm_l.obcc" "Skirt_skinCluster.ifcl[10]";
connectAttr "lowerarm_l.obcc" "Skirt_skinCluster.ifcl[11]";
connectAttr "lowerarm_twist_02_l.obcc" "Skirt_skinCluster.ifcl[12]";
connectAttr "lowerarm_twist_01_l.obcc" "Skirt_skinCluster.ifcl[13]";
connectAttr "hand_l.obcc" "Skirt_skinCluster.ifcl[14]";
connectAttr "middle_metacarpal_l.obcc" "Skirt_skinCluster.ifcl[15]";
connectAttr "middle_01_l.obcc" "Skirt_skinCluster.ifcl[16]";
connectAttr "middle_02_l.obcc" "Skirt_skinCluster.ifcl[17]";
connectAttr "middle_03_l.obcc" "Skirt_skinCluster.ifcl[18]";
connectAttr "pinky_metacarpal_l.obcc" "Skirt_skinCluster.ifcl[19]";
connectAttr "pinky_01_l.obcc" "Skirt_skinCluster.ifcl[20]";
connectAttr "pinky_02_l.obcc" "Skirt_skinCluster.ifcl[21]";
connectAttr "pinky_03_l.obcc" "Skirt_skinCluster.ifcl[22]";
connectAttr "ring_metacarpal_l.obcc" "Skirt_skinCluster.ifcl[23]";
connectAttr "ring_01_l.obcc" "Skirt_skinCluster.ifcl[24]";
connectAttr "ring_02_l.obcc" "Skirt_skinCluster.ifcl[25]";
connectAttr "ring_03_l.obcc" "Skirt_skinCluster.ifcl[26]";
connectAttr "thumb_01_l.obcc" "Skirt_skinCluster.ifcl[27]";
connectAttr "thumb_02_l.obcc" "Skirt_skinCluster.ifcl[28]";
connectAttr "thumb_03_l.obcc" "Skirt_skinCluster.ifcl[29]";
connectAttr "index_metacarpal_l.obcc" "Skirt_skinCluster.ifcl[30]";
connectAttr "index_01_l.obcc" "Skirt_skinCluster.ifcl[31]";
connectAttr "index_02_l.obcc" "Skirt_skinCluster.ifcl[32]";
connectAttr "index_03_l.obcc" "Skirt_skinCluster.ifcl[33]";
connectAttr "upperarm_twist_01_l.obcc" "Skirt_skinCluster.ifcl[34]";
connectAttr "upperarm_twist_02_l.obcc" "Skirt_skinCluster.ifcl[35]";
connectAttr "clavicle_r.obcc" "Skirt_skinCluster.ifcl[36]";
connectAttr "upperarm_r.obcc" "Skirt_skinCluster.ifcl[37]";
connectAttr "lowerarm_r.obcc" "Skirt_skinCluster.ifcl[38]";
connectAttr "lowerarm_twist_02_r.obcc" "Skirt_skinCluster.ifcl[39]";
connectAttr "lowerarm_twist_01_r.obcc" "Skirt_skinCluster.ifcl[40]";
connectAttr "hand_r.obcc" "Skirt_skinCluster.ifcl[41]";
connectAttr "middle_metacarpal_r.obcc" "Skirt_skinCluster.ifcl[42]";
connectAttr "middle_01_r.obcc" "Skirt_skinCluster.ifcl[43]";
connectAttr "middle_02_r.obcc" "Skirt_skinCluster.ifcl[44]";
connectAttr "middle_03_r.obcc" "Skirt_skinCluster.ifcl[45]";
connectAttr "pinky_metacarpal_r.obcc" "Skirt_skinCluster.ifcl[46]";
connectAttr "pinky_01_r.obcc" "Skirt_skinCluster.ifcl[47]";
connectAttr "pinky_02_r.obcc" "Skirt_skinCluster.ifcl[48]";
connectAttr "pinky_03_r.obcc" "Skirt_skinCluster.ifcl[49]";
connectAttr "ring_metacarpal_r.obcc" "Skirt_skinCluster.ifcl[50]";
connectAttr "ring_01_r.obcc" "Skirt_skinCluster.ifcl[51]";
connectAttr "ring_02_r.obcc" "Skirt_skinCluster.ifcl[52]";
connectAttr "ring_03_r.obcc" "Skirt_skinCluster.ifcl[53]";
connectAttr "thumb_01_r.obcc" "Skirt_skinCluster.ifcl[54]";
connectAttr "thumb_02_r.obcc" "Skirt_skinCluster.ifcl[55]";
connectAttr "thumb_03_r.obcc" "Skirt_skinCluster.ifcl[56]";
connectAttr "index_metacarpal_r.obcc" "Skirt_skinCluster.ifcl[57]";
connectAttr "index_01_r.obcc" "Skirt_skinCluster.ifcl[58]";
connectAttr "index_02_r.obcc" "Skirt_skinCluster.ifcl[59]";
connectAttr "index_03_r.obcc" "Skirt_skinCluster.ifcl[60]";
connectAttr "upperarm_twist_01_r.obcc" "Skirt_skinCluster.ifcl[61]";
connectAttr "upperarm_twist_02_r.obcc" "Skirt_skinCluster.ifcl[62]";
connectAttr "thigh_r.obcc" "Skirt_skinCluster.ifcl[63]";
connectAttr "calf_r.obcc" "Skirt_skinCluster.ifcl[64]";
connectAttr "foot_r.obcc" "Skirt_skinCluster.ifcl[65]";
connectAttr "ball_r.obcc" "Skirt_skinCluster.ifcl[66]";
connectAttr "calf_twist_02_r.obcc" "Skirt_skinCluster.ifcl[67]";
connectAttr "calf_twist_01_r.obcc" "Skirt_skinCluster.ifcl[68]";
connectAttr "thigh_twist_01_r.obcc" "Skirt_skinCluster.ifcl[69]";
connectAttr "thigh_twist_02_r.obcc" "Skirt_skinCluster.ifcl[70]";
connectAttr "thigh_l.obcc" "Skirt_skinCluster.ifcl[71]";
connectAttr "calf_l.obcc" "Skirt_skinCluster.ifcl[72]";
connectAttr "foot_l.obcc" "Skirt_skinCluster.ifcl[73]";
connectAttr "ball_l.obcc" "Skirt_skinCluster.ifcl[74]";
connectAttr "calf_twist_02_l.obcc" "Skirt_skinCluster.ifcl[75]";
connectAttr "calf_twist_01_l.obcc" "Skirt_skinCluster.ifcl[76]";
connectAttr "thigh_twist_01_l.obcc" "Skirt_skinCluster.ifcl[77]";
connectAttr "thigh_twist_02_l.obcc" "Skirt_skinCluster.ifcl[78]";
connectAttr "bindPose1.msg" "Skirt_skinCluster.bp";
connectAttr "root.msg" "bindPose1.m[0]";
connectAttr "pelvis.msg" "bindPose1.m[1]";
connectAttr "spine_01.msg" "bindPose1.m[2]";
connectAttr "spine_02.msg" "bindPose1.m[3]";
connectAttr "spine_03.msg" "bindPose1.m[4]";
connectAttr "spine_04.msg" "bindPose1.m[5]";
connectAttr "spine_05.msg" "bindPose1.m[6]";
connectAttr "neck_01.msg" "bindPose1.m[7]";
connectAttr "neck_02.msg" "bindPose1.m[8]";
connectAttr "head.msg" "bindPose1.m[9]";
connectAttr "clavicle_l.msg" "bindPose1.m[10]";
connectAttr "upperarm_l.msg" "bindPose1.m[11]";
connectAttr "lowerarm_l.msg" "bindPose1.m[12]";
connectAttr "lowerarm_twist_02_l.msg" "bindPose1.m[13]";
connectAttr "lowerarm_twist_01_l.msg" "bindPose1.m[14]";
connectAttr "hand_l.msg" "bindPose1.m[15]";
connectAttr "middle_metacarpal_l.msg" "bindPose1.m[16]";
connectAttr "middle_01_l.msg" "bindPose1.m[17]";
connectAttr "middle_02_l.msg" "bindPose1.m[18]";
connectAttr "middle_03_l.msg" "bindPose1.m[19]";
connectAttr "pinky_metacarpal_l.msg" "bindPose1.m[20]";
connectAttr "pinky_01_l.msg" "bindPose1.m[21]";
connectAttr "pinky_02_l.msg" "bindPose1.m[22]";
connectAttr "pinky_03_l.msg" "bindPose1.m[23]";
connectAttr "ring_metacarpal_l.msg" "bindPose1.m[24]";
connectAttr "ring_01_l.msg" "bindPose1.m[25]";
connectAttr "ring_02_l.msg" "bindPose1.m[26]";
connectAttr "ring_03_l.msg" "bindPose1.m[27]";
connectAttr "thumb_01_l.msg" "bindPose1.m[28]";
connectAttr "thumb_02_l.msg" "bindPose1.m[29]";
connectAttr "thumb_03_l.msg" "bindPose1.m[30]";
connectAttr "index_metacarpal_l.msg" "bindPose1.m[31]";
connectAttr "index_01_l.msg" "bindPose1.m[32]";
connectAttr "index_02_l.msg" "bindPose1.m[33]";
connectAttr "index_03_l.msg" "bindPose1.m[34]";
connectAttr "weapon_l.msg" "bindPose1.m[35]";
connectAttr "upperarm_twist_01_l.msg" "bindPose1.m[36]";
connectAttr "upperarm_twist_02_l.msg" "bindPose1.m[37]";
connectAttr "clavicle_r.msg" "bindPose1.m[38]";
connectAttr "upperarm_r.msg" "bindPose1.m[39]";
connectAttr "lowerarm_r.msg" "bindPose1.m[40]";
connectAttr "lowerarm_twist_02_r.msg" "bindPose1.m[41]";
connectAttr "lowerarm_twist_01_r.msg" "bindPose1.m[42]";
connectAttr "hand_r.msg" "bindPose1.m[43]";
connectAttr "middle_metacarpal_r.msg" "bindPose1.m[44]";
connectAttr "middle_01_r.msg" "bindPose1.m[45]";
connectAttr "middle_02_r.msg" "bindPose1.m[46]";
connectAttr "middle_03_r.msg" "bindPose1.m[47]";
connectAttr "pinky_metacarpal_r.msg" "bindPose1.m[48]";
connectAttr "pinky_01_r.msg" "bindPose1.m[49]";
connectAttr "pinky_02_r.msg" "bindPose1.m[50]";
connectAttr "pinky_03_r.msg" "bindPose1.m[51]";
connectAttr "ring_metacarpal_r.msg" "bindPose1.m[52]";
connectAttr "ring_01_r.msg" "bindPose1.m[53]";
connectAttr "ring_02_r.msg" "bindPose1.m[54]";
connectAttr "ring_03_r.msg" "bindPose1.m[55]";
connectAttr "thumb_01_r.msg" "bindPose1.m[56]";
connectAttr "thumb_02_r.msg" "bindPose1.m[57]";
connectAttr "thumb_03_r.msg" "bindPose1.m[58]";
connectAttr "index_metacarpal_r.msg" "bindPose1.m[59]";
connectAttr "index_01_r.msg" "bindPose1.m[60]";
connectAttr "index_02_r.msg" "bindPose1.m[61]";
connectAttr "index_03_r.msg" "bindPose1.m[62]";
connectAttr "weapon_r.msg" "bindPose1.m[63]";
connectAttr "upperarm_twist_01_r.msg" "bindPose1.m[64]";
connectAttr "upperarm_twist_02_r.msg" "bindPose1.m[65]";
connectAttr "thigh_r.msg" "bindPose1.m[66]";
connectAttr "calf_r.msg" "bindPose1.m[67]";
connectAttr "foot_r.msg" "bindPose1.m[68]";
connectAttr "ball_r.msg" "bindPose1.m[69]";
connectAttr "calf_twist_02_r.msg" "bindPose1.m[70]";
connectAttr "calf_twist_01_r.msg" "bindPose1.m[71]";
connectAttr "thigh_twist_01_r.msg" "bindPose1.m[72]";
connectAttr "thigh_twist_02_r.msg" "bindPose1.m[73]";
connectAttr "thigh_l.msg" "bindPose1.m[74]";
connectAttr "calf_l.msg" "bindPose1.m[75]";
connectAttr "foot_l.msg" "bindPose1.m[76]";
connectAttr "ball_l.msg" "bindPose1.m[77]";
connectAttr "calf_twist_02_l.msg" "bindPose1.m[78]";
connectAttr "calf_twist_01_l.msg" "bindPose1.m[79]";
connectAttr "thigh_twist_01_l.msg" "bindPose1.m[80]";
connectAttr "thigh_twist_02_l.msg" "bindPose1.m[81]";
connectAttr "ik_hand_root.msg" "bindPose1.m[82]";
connectAttr "ik_hand_gun.msg" "bindPose1.m[83]";
connectAttr "ik_hand_r.msg" "bindPose1.m[84]";
connectAttr "ik_hand_l.msg" "bindPose1.m[85]";
connectAttr "ik_foot_root.msg" "bindPose1.m[86]";
connectAttr "ik_foot_l.msg" "bindPose1.m[87]";
connectAttr "ik_foot_r.msg" "bindPose1.m[88]";
connectAttr "interaction.msg" "bindPose1.m[89]";
connectAttr "center_of_mass.msg" "bindPose1.m[90]";
connectAttr "camera_root.msg" "bindPose1.m[91]";
connectAttr "camera_bone.msg" "bindPose1.m[92]";
connectAttr "bindPose1.w" "bindPose1.p[0]";
connectAttr "bindPose1.m[0]" "bindPose1.p[1]";
connectAttr "bindPose1.m[1]" "bindPose1.p[2]";
connectAttr "bindPose1.m[2]" "bindPose1.p[3]";
connectAttr "bindPose1.m[3]" "bindPose1.p[4]";
connectAttr "bindPose1.m[4]" "bindPose1.p[5]";
connectAttr "bindPose1.m[5]" "bindPose1.p[6]";
connectAttr "bindPose1.m[6]" "bindPose1.p[7]";
connectAttr "bindPose1.m[7]" "bindPose1.p[8]";
connectAttr "bindPose1.m[8]" "bindPose1.p[9]";
connectAttr "bindPose1.m[6]" "bindPose1.p[10]";
connectAttr "bindPose1.m[10]" "bindPose1.p[11]";
connectAttr "bindPose1.m[11]" "bindPose1.p[12]";
connectAttr "bindPose1.m[12]" "bindPose1.p[13]";
connectAttr "bindPose1.m[12]" "bindPose1.p[14]";
connectAttr "bindPose1.m[12]" "bindPose1.p[15]";
connectAttr "bindPose1.m[15]" "bindPose1.p[16]";
connectAttr "bindPose1.m[16]" "bindPose1.p[17]";
connectAttr "bindPose1.m[17]" "bindPose1.p[18]";
connectAttr "bindPose1.m[18]" "bindPose1.p[19]";
connectAttr "bindPose1.m[15]" "bindPose1.p[20]";
connectAttr "bindPose1.m[20]" "bindPose1.p[21]";
connectAttr "bindPose1.m[21]" "bindPose1.p[22]";
connectAttr "bindPose1.m[22]" "bindPose1.p[23]";
connectAttr "bindPose1.m[15]" "bindPose1.p[24]";
connectAttr "bindPose1.m[24]" "bindPose1.p[25]";
connectAttr "bindPose1.m[25]" "bindPose1.p[26]";
connectAttr "bindPose1.m[26]" "bindPose1.p[27]";
connectAttr "bindPose1.m[15]" "bindPose1.p[28]";
connectAttr "bindPose1.m[28]" "bindPose1.p[29]";
connectAttr "bindPose1.m[29]" "bindPose1.p[30]";
connectAttr "bindPose1.m[15]" "bindPose1.p[31]";
connectAttr "bindPose1.m[31]" "bindPose1.p[32]";
connectAttr "bindPose1.m[32]" "bindPose1.p[33]";
connectAttr "bindPose1.m[33]" "bindPose1.p[34]";
connectAttr "bindPose1.m[15]" "bindPose1.p[35]";
connectAttr "bindPose1.m[11]" "bindPose1.p[36]";
connectAttr "bindPose1.m[11]" "bindPose1.p[37]";
connectAttr "bindPose1.m[6]" "bindPose1.p[38]";
connectAttr "bindPose1.m[38]" "bindPose1.p[39]";
connectAttr "bindPose1.m[39]" "bindPose1.p[40]";
connectAttr "bindPose1.m[40]" "bindPose1.p[41]";
connectAttr "bindPose1.m[40]" "bindPose1.p[42]";
connectAttr "bindPose1.m[40]" "bindPose1.p[43]";
connectAttr "bindPose1.m[43]" "bindPose1.p[44]";
connectAttr "bindPose1.m[44]" "bindPose1.p[45]";
connectAttr "bindPose1.m[45]" "bindPose1.p[46]";
connectAttr "bindPose1.m[46]" "bindPose1.p[47]";
connectAttr "bindPose1.m[43]" "bindPose1.p[48]";
connectAttr "bindPose1.m[48]" "bindPose1.p[49]";
connectAttr "bindPose1.m[49]" "bindPose1.p[50]";
connectAttr "bindPose1.m[50]" "bindPose1.p[51]";
connectAttr "bindPose1.m[43]" "bindPose1.p[52]";
connectAttr "bindPose1.m[52]" "bindPose1.p[53]";
connectAttr "bindPose1.m[53]" "bindPose1.p[54]";
connectAttr "bindPose1.m[54]" "bindPose1.p[55]";
connectAttr "bindPose1.m[43]" "bindPose1.p[56]";
connectAttr "bindPose1.m[56]" "bindPose1.p[57]";
connectAttr "bindPose1.m[57]" "bindPose1.p[58]";
connectAttr "bindPose1.m[43]" "bindPose1.p[59]";
connectAttr "bindPose1.m[59]" "bindPose1.p[60]";
connectAttr "bindPose1.m[60]" "bindPose1.p[61]";
connectAttr "bindPose1.m[61]" "bindPose1.p[62]";
connectAttr "bindPose1.m[43]" "bindPose1.p[63]";
connectAttr "bindPose1.m[39]" "bindPose1.p[64]";
connectAttr "bindPose1.m[39]" "bindPose1.p[65]";
connectAttr "bindPose1.m[1]" "bindPose1.p[66]";
connectAttr "bindPose1.m[66]" "bindPose1.p[67]";
connectAttr "bindPose1.m[67]" "bindPose1.p[68]";
connectAttr "bindPose1.m[68]" "bindPose1.p[69]";
connectAttr "bindPose1.m[67]" "bindPose1.p[70]";
connectAttr "bindPose1.m[67]" "bindPose1.p[71]";
connectAttr "bindPose1.m[66]" "bindPose1.p[72]";
connectAttr "bindPose1.m[66]" "bindPose1.p[73]";
connectAttr "bindPose1.m[1]" "bindPose1.p[74]";
connectAttr "bindPose1.m[74]" "bindPose1.p[75]";
connectAttr "bindPose1.m[75]" "bindPose1.p[76]";
connectAttr "bindPose1.m[76]" "bindPose1.p[77]";
connectAttr "bindPose1.m[75]" "bindPose1.p[78]";
connectAttr "bindPose1.m[75]" "bindPose1.p[79]";
connectAttr "bindPose1.m[74]" "bindPose1.p[80]";
connectAttr "bindPose1.m[74]" "bindPose1.p[81]";
connectAttr "bindPose1.m[0]" "bindPose1.p[82]";
connectAttr "bindPose1.m[82]" "bindPose1.p[83]";
connectAttr "bindPose1.m[83]" "bindPose1.p[84]";
connectAttr "bindPose1.m[83]" "bindPose1.p[85]";
connectAttr "bindPose1.m[0]" "bindPose1.p[86]";
connectAttr "bindPose1.m[86]" "bindPose1.p[87]";
connectAttr "bindPose1.m[86]" "bindPose1.p[88]";
connectAttr "bindPose1.m[0]" "bindPose1.p[89]";
connectAttr "bindPose1.m[0]" "bindPose1.p[90]";
connectAttr "bindPose1.m[0]" "bindPose1.p[91]";
connectAttr "bindPose1.m[91]" "bindPose1.p[92]";
connectAttr "root.bps" "bindPose1.wm[0]";
connectAttr "pelvis.bps" "bindPose1.wm[1]";
connectAttr "spine_01.bps" "bindPose1.wm[2]";
connectAttr "spine_02.bps" "bindPose1.wm[3]";
connectAttr "spine_03.bps" "bindPose1.wm[4]";
connectAttr "spine_04.bps" "bindPose1.wm[5]";
connectAttr "spine_05.bps" "bindPose1.wm[6]";
connectAttr "neck_01.bps" "bindPose1.wm[7]";
connectAttr "neck_02.bps" "bindPose1.wm[8]";
connectAttr "head.bps" "bindPose1.wm[9]";
connectAttr "clavicle_l.bps" "bindPose1.wm[10]";
connectAttr "upperarm_l.bps" "bindPose1.wm[11]";
connectAttr "lowerarm_l.bps" "bindPose1.wm[12]";
connectAttr "lowerarm_twist_02_l.bps" "bindPose1.wm[13]";
connectAttr "lowerarm_twist_01_l.bps" "bindPose1.wm[14]";
connectAttr "hand_l.bps" "bindPose1.wm[15]";
connectAttr "middle_metacarpal_l.bps" "bindPose1.wm[16]";
connectAttr "middle_01_l.bps" "bindPose1.wm[17]";
connectAttr "middle_02_l.bps" "bindPose1.wm[18]";
connectAttr "middle_03_l.bps" "bindPose1.wm[19]";
connectAttr "pinky_metacarpal_l.bps" "bindPose1.wm[20]";
connectAttr "pinky_01_l.bps" "bindPose1.wm[21]";
connectAttr "pinky_02_l.bps" "bindPose1.wm[22]";
connectAttr "pinky_03_l.bps" "bindPose1.wm[23]";
connectAttr "ring_metacarpal_l.bps" "bindPose1.wm[24]";
connectAttr "ring_01_l.bps" "bindPose1.wm[25]";
connectAttr "ring_02_l.bps" "bindPose1.wm[26]";
connectAttr "ring_03_l.bps" "bindPose1.wm[27]";
connectAttr "thumb_01_l.bps" "bindPose1.wm[28]";
connectAttr "thumb_02_l.bps" "bindPose1.wm[29]";
connectAttr "thumb_03_l.bps" "bindPose1.wm[30]";
connectAttr "index_metacarpal_l.bps" "bindPose1.wm[31]";
connectAttr "index_01_l.bps" "bindPose1.wm[32]";
connectAttr "index_02_l.bps" "bindPose1.wm[33]";
connectAttr "index_03_l.bps" "bindPose1.wm[34]";
connectAttr "weapon_l.bps" "bindPose1.wm[35]";
connectAttr "upperarm_twist_01_l.bps" "bindPose1.wm[36]";
connectAttr "upperarm_twist_02_l.bps" "bindPose1.wm[37]";
connectAttr "clavicle_r.bps" "bindPose1.wm[38]";
connectAttr "upperarm_r.bps" "bindPose1.wm[39]";
connectAttr "lowerarm_r.bps" "bindPose1.wm[40]";
connectAttr "lowerarm_twist_02_r.bps" "bindPose1.wm[41]";
connectAttr "lowerarm_twist_01_r.bps" "bindPose1.wm[42]";
connectAttr "hand_r.bps" "bindPose1.wm[43]";
connectAttr "middle_metacarpal_r.bps" "bindPose1.wm[44]";
connectAttr "middle_01_r.bps" "bindPose1.wm[45]";
connectAttr "middle_02_r.bps" "bindPose1.wm[46]";
connectAttr "middle_03_r.bps" "bindPose1.wm[47]";
connectAttr "pinky_metacarpal_r.bps" "bindPose1.wm[48]";
connectAttr "pinky_01_r.bps" "bindPose1.wm[49]";
connectAttr "pinky_02_r.bps" "bindPose1.wm[50]";
connectAttr "pinky_03_r.bps" "bindPose1.wm[51]";
connectAttr "ring_metacarpal_r.bps" "bindPose1.wm[52]";
connectAttr "ring_01_r.bps" "bindPose1.wm[53]";
connectAttr "ring_02_r.bps" "bindPose1.wm[54]";
connectAttr "ring_03_r.bps" "bindPose1.wm[55]";
connectAttr "thumb_01_r.bps" "bindPose1.wm[56]";
connectAttr "thumb_02_r.bps" "bindPose1.wm[57]";
connectAttr "thumb_03_r.bps" "bindPose1.wm[58]";
connectAttr "index_metacarpal_r.bps" "bindPose1.wm[59]";
connectAttr "index_01_r.bps" "bindPose1.wm[60]";
connectAttr "index_02_r.bps" "bindPose1.wm[61]";
connectAttr "index_03_r.bps" "bindPose1.wm[62]";
connectAttr "weapon_r.bps" "bindPose1.wm[63]";
connectAttr "upperarm_twist_01_r.bps" "bindPose1.wm[64]";
connectAttr "upperarm_twist_02_r.bps" "bindPose1.wm[65]";
connectAttr "thigh_r.bps" "bindPose1.wm[66]";
connectAttr "calf_r.bps" "bindPose1.wm[67]";
connectAttr "foot_r.bps" "bindPose1.wm[68]";
connectAttr "ball_r.bps" "bindPose1.wm[69]";
connectAttr "calf_twist_02_r.bps" "bindPose1.wm[70]";
connectAttr "calf_twist_01_r.bps" "bindPose1.wm[71]";
connectAttr "thigh_twist_01_r.bps" "bindPose1.wm[72]";
connectAttr "thigh_twist_02_r.bps" "bindPose1.wm[73]";
connectAttr "thigh_l.bps" "bindPose1.wm[74]";
connectAttr "calf_l.bps" "bindPose1.wm[75]";
connectAttr "foot_l.bps" "bindPose1.wm[76]";
connectAttr "ball_l.bps" "bindPose1.wm[77]";
connectAttr "calf_twist_02_l.bps" "bindPose1.wm[78]";
connectAttr "calf_twist_01_l.bps" "bindPose1.wm[79]";
connectAttr "thigh_twist_01_l.bps" "bindPose1.wm[80]";
connectAttr "thigh_twist_02_l.bps" "bindPose1.wm[81]";
connectAttr "ik_hand_root.bps" "bindPose1.wm[82]";
connectAttr "ik_hand_gun.bps" "bindPose1.wm[83]";
connectAttr "ik_hand_r.bps" "bindPose1.wm[84]";
connectAttr "ik_hand_l.bps" "bindPose1.wm[85]";
connectAttr "ik_foot_root.bps" "bindPose1.wm[86]";
connectAttr "ik_foot_l.bps" "bindPose1.wm[87]";
connectAttr "ik_foot_r.bps" "bindPose1.wm[88]";
connectAttr "interaction.bps" "bindPose1.wm[89]";
connectAttr "center_of_mass.bps" "bindPose1.wm[90]";
connectAttr "camera_root.bps" "bindPose1.wm[91]";
connectAttr "camera_bone.bps" "bindPose1.wm[92]";
connectAttr "defaultRenderLayer.msg" ":defaultRenderingList1.r" -na;
connectAttr "SkirtShape.iog" ":initialShadingGroup.dsm" -na;
// End of MainHero_Skirt.ma
