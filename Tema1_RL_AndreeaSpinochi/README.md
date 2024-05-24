1 2
### Implementare switch ###
---------------------------------

1. Tabela de comutare
Pentru primul subpunct am folosit pseudocodul oferit in cerinta temei, adaugand dictionarul MAC_Table
care mapeaza adresa MAC la port(in cazul nostru, adresa MAC sursa la portul sursa)
Pseudocul este urmatorul:
```MAC_Table[src] = P
if is_unicast(dst):
    if dst in MAC_Table:
        forward_frame(F, MAC_Table[dst])
    else:
        for o in Ports:
          if o != P:
               forward_frame(F, o)
else:
    # trimite cadrul pe toate celelalte porturi
    for o in Ports:
        if o != P:
            forward_frame(F, o)```

2. VLAN si trunking
Pentru al doilea subpunct al temei am folosit pseudocodul atasat anterior. Am creat un dictionar numit interface_type
unde am mapat fiecare port la tipul acestuia('T' - trunk sau numarul vlan-ului daca acesta era access). Am citit apoi
din fisierele de config numele interfetelor si le-am mapat la tipul lor.
Datele astea le-am adaugat la codul descris anterior, pentru ca switch-ul sa poata trimita frame-urile in functie de
vlan. Pentru fiecare caz din cele 3 prezentate inainte (daca mesajul este unicast si daca se afla in tabela de comutare sau nu),
am adaugat urmatoarea verificare:
1. Daca ambele porturi sunt access si vlan-ul sursa cu cel destinatie sunt egale, atunci frame-ul de trimite
2. Daca ambele sunt trunk, atunci frame-ul se trimite exact asa cum a venit
3. Atunci cand pachetul trece din access in trunk, se adauga tag-ul de vlan si se trimite mai departe
4. Atunci cand pachetul trece din trunk in access, tag-ul pachetului se indeparteaza si se verifica daca vlan-ul
sursa este egal cu cel destinatie. Daca da, atunci se trimite frame-ul mai departe, altfel se ignora.